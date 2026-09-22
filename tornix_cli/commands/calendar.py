"""Calendar meetings — the surface the Tornix UI calls "اجتماع".

WHY THIS MODULE EXISTS
----------------------
Before it, the only meeting command was `tornix meetings room-create`, which
writes ONE row into `video_rooms`. The calendar screen does not read that table:
it reads `calendar_events`. So an agent that "created a meeting" produced a room
nobody could find on their calendar, with no attendees and no notification —
the exact complaint this module answers.

A meeting in Tornix is THREE things written together, and the frontend's own
add-event modal is the specification:

  1. a `video_rooms` row whose `metadata` carries `scheduledStartDate` /
     `scheduledEndDate` / `calendarEventTitle` / `invitedParticipants`. The
     Meetings tab reads `metadata.scheduledStartDate` to tell a SCHEDULED
     meeting from an ad-hoc "quick room"; without it the room renders bare.
  2. a `calendar_events` row carrying `title`, `start_date`, `end_date`,
     `participants[]`, `meeting_link` and `video_room_id`. This is what puts
     the meeting on a calendar — everybody's, not just the creator's.
  3. nothing: the invitation is not a third call. The NestJS data proxy fires
     `handleCalendarEventDataProxy` on INSERT *and* UPDATE of `calendar_events`
     and notifies every participant carrying an `id`.

That last point is the reason every write here goes through `/api/v1/data/...`
and NOT through `PATCH /api/v1/calendar/events/{id}`. The dedicated route is a
direct Prisma update with no data-proxy event hook, so adding an attendee
through it is silent. The proxy path is the one that pings people.

SCOPING
-------
`calendar_events` has no `organization_id`; the proxy scopes it by `user_id`,
the CREATOR. Reads, updates and deletes through the proxy therefore only ever
see meetings this caller booked — which is right for an agent acting on the
user's behalf, but it means a PATCH against somebody else's meeting matches no
row and comes back `{"count": 0}` instead of an error. Every mutating command
below checks for that and raises, because a silent no-op is the worst possible
answer to "add Ahmed to the meeting".

Listing is the exception: it goes through `GET /api/v1/calendar/my-events`,
which returns meetings you created AND meetings you were invited to.
"""
from __future__ import annotations

import time as _time
import uuid as _uuid
from datetime import datetime, timedelta, timezone

import click

from ._helpers import client, show

EVENTS = "calendar_events"
ROOMS = "video_rooms"

#: `MAX_RANGE_DAYS` in `src/modules/calendar/calendar.controller.ts`. Asking for
#: more is a 400, so the default window stays comfortably inside it.
MAX_RANGE_DAYS = 120

#: The colour the UI gives an ordinary event when the user picks none. A literal
#: `var(--...)` string is what the frontend actually stores in this column.
DEFAULT_COLOR = "var(--color-purple-based)"

#: Route of the meeting room in the web app (`ROUTES.DASHBOARD_MEETINGS`).
MEETINGS_ROUTE = "/dashboard/meetings"


# ── time helpers ──────────────────────────────────────────────────────────


def _iso(value: str, flag: str) -> datetime:
    """Parse a user-supplied instant. Accepts `2026-10-01T14:00:00Z`,
    `2026-10-01T14:00` and `2026-10-01 14:00`; a bare date means midnight.

    A naive value is read as UTC rather than as the machine's local time: the
    agent runs in a container whose clock is UTC, so guessing "local" would
    silently move every meeting by the host's offset."""
    raw = value.strip().replace(" ", "T")
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        raise click.UsageError(
            f"{flag} must be an ISO instant (e.g. 2026-10-01T14:00:00Z), got {value!r}"
        )
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def _utc(dt: datetime) -> str:
    """Serialize exactly as the frontend does — `toISOString()`, i.e. UTC with
    a trailing `Z` and milliseconds."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + \
        f"{dt.astimezone(timezone.utc).microsecond // 1000:03d}Z"


# ── people ────────────────────────────────────────────────────────────────


def _me(c) -> dict:
    """The caller's own profile — `user_id` on a calendar event is NOT stamped
    by the proxy, and the column is NOT NULL, so every create must supply it."""
    me = c.get("/api/v1/users/me")
    if isinstance(me, dict) and isinstance(me.get("user"), dict):
        me = me["user"]
    if not isinstance(me, dict) or not me.get("id"):
        raise click.ClickException(
            "could not resolve the signed-in user from /users/me — cannot stamp "
            "calendar_events.user_id (the column is NOT NULL)."
        )
    return me


def _org_members(c, org_id: str) -> list[dict]:
    """Flatten `GET /organizations/{id}/members` into `{id, name, email}`.

    The route returns `organization_member` rows with a nested `user` that
    carries the `profile`; `full_name` lives on the profile, the address on the
    user. Anything unresolvable is dropped rather than half-built — a
    participant with no `id` is invisible to the notifier."""
    rows = c.get(f"/api/v1/organizations/{org_id}/members")
    out: list[dict] = []
    for row in rows or []:
        user = row.get("user") if isinstance(row, dict) else None
        if not isinstance(user, dict):
            continue
        uid = user.get("id") or row.get("user_id")
        if not uid:
            continue
        profile = user.get("profile") if isinstance(user.get("profile"), dict) else {}
        out.append({
            "id": uid,
            "name": (profile.get("full_name") or user.get("email") or "").strip(),
            "email": (user.get("email") or profile.get("email") or "").strip(),
        })
    return out


def _resolve_attendees(c, org_id: str, needles: tuple[str, ...]) -> list[dict]:
    """Turn `--attendee` values into calendar participant objects.

    A needle may be a user uuid, an e-mail, or a (partial, case-insensitive)
    name. Resolution is deliberately STRICT: an unknown or ambiguous needle
    raises instead of being dropped, because the failure mode this module was
    written to kill is "the meeting was created but nobody was invited" — and a
    silently skipped attendee is the same bug in a smaller box.

    The shape is the frontend's `Participant`: `{id, name, email,
    responseStatus}`. `responseStatus: 'needsAction'` is what the add-event
    modal writes for a freshly invited person."""
    if not needles:
        return []
    members = _org_members(c, org_id)
    by_id = {m["id"]: m for m in members}
    by_email = {m["email"].lower(): m for m in members if m["email"]}

    resolved: list[dict] = []
    for needle in needles:
        key = needle.strip()
        if not key:
            continue
        hit = by_id.get(key) or by_email.get(key.lower())
        if hit is None:
            low = key.lower()
            matches = [m for m in members if low in m["name"].lower()]
            if len(matches) > 1:
                names = ", ".join(f'{m["name"]} <{m["email"]}>' for m in matches[:5])
                raise click.UsageError(
                    f"--attendee {key!r} matches {len(matches)} people ({names}). "
                    "Use the e-mail or the user id."
                )
            if not matches:
                raise click.UsageError(
                    f"--attendee {key!r} matched nobody in this organization. "
                    "Run `tornix calendar members --json` to see who is in it."
                )
            hit = matches[0]
        resolved.append({
            "id": hit["id"],
            "name": hit["name"],
            "email": hit["email"],
            "responseStatus": "needsAction",
        })

    # De-duplicate, preserving order: inviting the same person twice would show
    # them twice on the card and claim two notifier slots.
    seen: set[str] = set()
    unique: list[dict] = []
    for p in resolved:
        if p["id"] in seen:
            continue
        seen.add(p["id"])
        unique.append(p)
    return unique


# ── proxy helpers ─────────────────────────────────────────────────────────


def _get_event(c, event_id: str) -> dict:
    """Read one event through the proxy (creator-scoped, so this doubles as the
    "is it mine to change?" check)."""
    rows = c.get(f"/api/v1/data/{EVENTS}", params={"id": f"eq.{event_id}"})
    rows = rows if isinstance(rows, list) else ([rows] if rows else [])
    if not rows:
        raise click.ClickException(
            f"meeting {event_id} not found among the meetings you created. "
            "The calendar proxy scopes this table by creator, so a meeting "
            "somebody else booked cannot be changed here."
        )
    return rows[0]


def _assert_changed(result, event_id: str, what: str) -> None:
    """The proxy answers a filtered UPDATE/DELETE that matched nothing with
    `{"count": 0}` rather than an error (it maps Prisma's P2025 that way so a
    scoped-out row can never leak its existence). Left unchecked that reads to
    the agent as success, so it is turned back into a real failure here."""
    if isinstance(result, dict) and result.get("count") == 0:
        raise click.ClickException(
            f"{what} changed nothing for meeting {event_id} — you are not its "
            "creator, or it no longer exists."
        )


def _merge_room_invitees(c, room_id: str, participants: list[dict]) -> None:
    """Mirror the attendee list into the room's `metadata.invitedParticipants`,
    which is what draws the avatars and the "N invited" line on the meeting card.

    Read-modify-write, never a blind overwrite: `metadata` is one JSON column
    and replacing it wholesale drops `scheduledStartDate`, which demotes the
    meeting to a "quick room" in the UI. Note the shape differs from the
    calendar's — the room uses `fullName`, the calendar uses `name`.

    Best-effort by design: the room card is cosmetic, and failing the whole
    invite because an avatar list did not update would be the wrong trade."""
    try:
        rows = c.get(f"/api/v1/data/{ROOMS}", params={"id": f"eq.{room_id}"})
        rows = rows if isinstance(rows, list) else ([rows] if rows else [])
        existing = rows[0].get("metadata") if rows else None
        metadata = dict(existing) if isinstance(existing, dict) else {}
        metadata["invitedParticipants"] = [
            {"id": p["id"], "email": p.get("email", ""), "fullName": p.get("name", "")}
            for p in participants
        ]
        c.patch(f"/api/v1/data/{ROOMS}", params={"id": f"eq.{room_id}"},
                json={"metadata": metadata})
    except Exception:
        pass


# ── group ─────────────────────────────────────────────────────────────────


@click.group(name="calendar", help="Calendar meetings — schedule, invite, reschedule (curated).")
def calendar_group() -> None:
    pass


@calendar_group.command("members", help="People you can invite (this org's members).")
@click.option("--query", "needle", default=None, help="Filter by name or e-mail substring.")
@click.option("--org", "organization_id", default=None,
              help="Organization id (defaults to active config org).")
@click.pass_obj
def calendar_members(obj, needle, organization_id):
    c = client(obj)
    org_id = organization_id or obj["config"].org_id
    members = _org_members(c, org_id)
    if needle:
        low = needle.strip().lower()
        members = [m for m in members
                   if low in m["name"].lower() or low in m["email"].lower()]
    show(obj, members, columns=["id", "name", "email"])


@calendar_group.command("list", help="Your meetings in a window — yours AND ones you were invited to.")
@click.option("--from", "from_", default=None, help="ISO start of the window (default: now).")
@click.option("--to", "to_", default=None, help="ISO end of the window.")
@click.option("--days", default=7, type=int, show_default=True,
              help="Window length when --to is omitted.")
@click.pass_obj
def calendar_list(obj, from_, to_, days):
    """Reads `GET /calendar/my-events`, NOT the data proxy. The proxy scopes
    this table by creator, so a meeting a colleague booked you into can never
    come back through it — which is precisely the "I don't see it" complaint."""
    start = _iso(from_, "--from") if from_ else datetime.now(timezone.utc)
    if to_:
        end = _iso(to_, "--to")
    else:
        if days < 1:
            raise click.UsageError("--days must be at least 1.")
        end = start + timedelta(days=days)
    if end <= start:
        raise click.UsageError("--to must be after --from.")
    if (end - start).total_seconds() / 86400 > MAX_RANGE_DAYS:
        raise click.UsageError(f"the window must be {MAX_RANGE_DAYS} days or less.")

    show(obj, client(obj).get("/api/v1/calendar/my-events",
                              params={"from": _utc(start), "to": _utc(end)}),
         columns=["id", "title", "start_date", "end_date", "video_room_id"])


@calendar_group.command("show", help="One meeting you created, with its attendees.")
@click.argument("event_id")
@click.pass_obj
def calendar_show(obj, event_id):
    show(obj, _get_event(client(obj), event_id))


@calendar_group.command("create", help="Schedule a meeting: calendar entry + video room + invitations.")
@click.option("--title", required=True, help="What the meeting is called.")
@click.option("--start", "start_raw", required=True,
              help="ISO start instant, e.g. 2026-10-01T14:00:00Z.")
@click.option("--end", "end_raw", default=None,
              help="ISO end instant. Defaults to --duration after --start.")
@click.option("--duration", "duration_minutes", default=60, type=int, show_default=True,
              help="Length in minutes when --end is omitted.")
@click.option("--attendee", "attendees", multiple=True,
              help="Person to invite: user id, e-mail, or name. Repeatable.")
@click.option("--description", default=None)
@click.option("--location", default=None)
@click.option("--video/--no-video", "with_video", default=True, show_default=True,
              help="Mint a video room and link it. --no-video books time only.")
@click.option("--all-day", is_flag=True, default=False)
@click.option("--color", default=DEFAULT_COLOR, show_default=False,
              help="Event colour as stored by the UI.")
@click.option("--reminder", "reminder_minutes", default=10, type=int, show_default=True,
              help="Popup reminder, minutes before the start.")
@click.option("--org", "organization_id", default=None,
              help="Organization id (defaults to active config org).")
@click.option("--web-url", default=None,
              help="Origin of the web app for the join link. Defaults to the API "
                   "url, which is the same host in every deployed environment.")
@click.pass_obj
def calendar_create(obj, title, start_raw, end_raw, duration_minutes, attendees,
                    description, location, with_video, all_day, color,
                    reminder_minutes, organization_id, web_url):
    """Write the room, then the event. In that order on purpose: the event
    carries `video_room_id`, and the notification fires off the event's INSERT —
    so by the time anybody is told about the meeting, the room they are told to
    join already exists."""
    c = client(obj)
    org_id = organization_id or obj["config"].org_id
    if not org_id:
        raise click.UsageError("no organization in context — pass --org.")

    title = title.strip()
    if not title:
        raise click.UsageError("--title must not be blank.")

    start = _iso(start_raw, "--start")
    if end_raw:
        end = _iso(end_raw, "--end")
    else:
        if duration_minutes < 1:
            raise click.UsageError("--duration must be at least 1 minute.")
        end = start + timedelta(minutes=duration_minutes)
    if end <= start:
        raise click.UsageError("--end must be after --start.")

    # An all-day event spans the calendar day of --start, exactly as the modal
    # builds it (midnight → 23:59:59.999).
    if all_day:
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(hour=23, minute=59, second=59, microsecond=999000)

    # Resolved BEFORE anything is written: an unknown attendee must fail the
    # whole command, not leave a half-built meeting behind.
    participants = _resolve_attendees(c, org_id, attendees)
    me = _me(c)

    if end <= datetime.now(timezone.utc) and participants:
        click.echo(
            "note: this meeting has already ended, so no invitations will be "
            "sent — the notifier ignores past meetings.", err=True)

    room_id = None
    meeting_link = None
    if with_video:
        room_name = f"room-{org_id}-{int(_time.time() * 1000)}-{_uuid.uuid4().hex[:6]}"
        room = c.post(f"/api/v1/data/{ROOMS}", envelope=True, json={
            "name": title,
            "room_name": room_name,
            "organization_id": org_id,
            # Matches the modal: the invitees plus the host.
            "max_participants": len(participants) + 1 if participants else 50,
            "is_active": True,
            "created_by": me["id"],
            # WITHOUT scheduledStartDate the Meetings tab renders this as an
            # ad-hoc "quick room" — no time, no attendees, no edit-as-meeting.
            "metadata": {
                "scheduledStartDate": _utc(start),
                "scheduledEndDate": _utc(end),
                "calendarEventTitle": title,
                "invitedParticipants": [
                    {"id": p["id"], "email": p["email"], "fullName": p["name"]}
                    for p in participants
                ],
            },
        })
        room_id = room.get("id") if isinstance(room, dict) else None
        if not room_id:
            raise click.ClickException(
                "the video room was not created — refusing to book a meeting "
                "whose join link would point nowhere."
            )
        origin = (web_url or obj["config"].api_url or "").rstrip("/")
        meeting_link = f"{origin}{MEETINGS_ROUTE}/{room_id}" if origin else None

    event = c.post(f"/api/v1/data/{EVENTS}", envelope=True, json={
        # NOT stamped by the proxy, and NOT NULL in the schema.
        "user_id": me["id"],
        "title": title,
        "description": description or None,
        "location": location or None,
        "meeting_link": meeting_link,
        "start_date": _utc(start),
        "end_date": _utc(end),
        "is_all_day": all_day,
        "color": color,
        "reminders": [{"method": "popup", "minutes": reminder_minutes}],
        # This array IS the invitation: the proxy's INSERT hook notifies every
        # entry carrying an `id`.
        "participants": participants,
        "video_room_id": room_id,
    })
    show(obj, event)


@calendar_group.command("invite", help="Add people to a meeting you created (and notify them).")
@click.argument("event_id")
@click.option("--attendee", "attendees", multiple=True, required=True,
              help="Person to invite: user id, e-mail, or name. Repeatable.")
@click.option("--org", "organization_id", default=None)
@click.pass_obj
def calendar_invite(obj, event_id, attendees, organization_id):
    """Merge, never replace. `participants` is one JSON column, so writing the
    new people alone would un-invite everybody already in the meeting.

    The PATCH goes through the data proxy because that is the path the invite
    notification hangs off — `PATCH /calendar/events/{id}` updates the row
    silently."""
    c = client(obj)
    org_id = organization_id or obj["config"].org_id
    event = _get_event(c, event_id)

    current = event.get("participants")
    current = list(current) if isinstance(current, list) else []
    known = {p.get("id") for p in current if isinstance(p, dict) and p.get("id")}

    incoming = _resolve_attendees(c, org_id, attendees)
    added = [p for p in incoming if p["id"] not in known]
    if not added:
        click.echo("everybody named is already in this meeting — nothing to do.", err=True)
        show(obj, event)
        return

    merged = current + added
    result = c.patch(f"/api/v1/data/{EVENTS}", params={"id": f"eq.{event_id}"},
                     json={"participants": merged})
    _assert_changed(result, event_id, "invite")

    if event.get("video_room_id"):
        _merge_room_invitees(c, event["video_room_id"], merged)
    show(obj, result)


@calendar_group.command("uninvite", help="Remove people from a meeting you created.")
@click.argument("event_id")
@click.option("--attendee", "attendees", multiple=True, required=True,
              help="Person to remove: user id, e-mail, or name. Repeatable.")
@click.option("--org", "organization_id", default=None)
@click.pass_obj
def calendar_uninvite(obj, event_id, attendees, organization_id):
    """Removal is silent on purpose — the platform has no "you were removed"
    notification, so say so rather than implying the person was told."""
    c = client(obj)
    org_id = organization_id or obj["config"].org_id
    event = _get_event(c, event_id)

    current = event.get("participants")
    current = list(current) if isinstance(current, list) else []
    drop = {p["id"] for p in _resolve_attendees(c, org_id, attendees)}
    remaining = [p for p in current
                 if not (isinstance(p, dict) and p.get("id") in drop)]
    if len(remaining) == len(current):
        click.echo("nobody named was in this meeting — nothing to do.", err=True)
        show(obj, event)
        return

    result = c.patch(f"/api/v1/data/{EVENTS}", params={"id": f"eq.{event_id}"},
                     json={"participants": remaining})
    _assert_changed(result, event_id, "uninvite")
    if event.get("video_room_id"):
        _merge_room_invitees(c, event["video_room_id"], remaining)
    click.echo("removed — note that nobody is notified of a removal.", err=True)
    show(obj, result)


@calendar_group.command("update", help="Retitle or reschedule a meeting you created.")
@click.argument("event_id")
@click.option("--title", default=None)
@click.option("--start", "start_raw", default=None, help="New ISO start instant.")
@click.option("--end", "end_raw", default=None, help="New ISO end instant.")
@click.option("--description", default=None)
@click.option("--location", default=None)
@click.pass_obj
def calendar_update(obj, event_id, title, start_raw, end_raw, description, location):
    """Moving a meeting notifies NOBODY — the invite notification is claimed
    once per (event, person) and a reschedule does not release that slot. Tell
    the attendees yourself if it matters."""
    c = client(obj)
    patch: dict = {}
    if title is not None:
        cleaned = title.strip()
        if not cleaned:
            raise click.UsageError("--title must not be blank.")
        patch["title"] = cleaned
    if description is not None:
        patch["description"] = description or None
    if location is not None:
        patch["location"] = location or None

    if start_raw or end_raw:
        event = _get_event(c, event_id)
        was_start = _iso(str(event["start_date"]), "--start")
        was_end = _iso(str(event["end_date"]), "--end")

        # `--start` ALONE means "move the meeting", not "make it start later and
        # end at the same time". Holding the old end would refuse every
        # postponement past it ("push it to tomorrow 9am") and would silently
        # stretch or squash the shorter moves it did accept, so the duration
        # travels with the meeting unless a new end is given explicitly.
        if start_raw and not end_raw:
            start = _iso(start_raw, "--start")
            end = start + (was_end - was_start)
        else:
            start = _iso(start_raw, "--start") if start_raw else was_start
            end = _iso(end_raw, "--end")
        if end <= start:
            raise click.UsageError("--end must be after --start.")
        patch["start_date"] = _utc(start)
        patch["end_date"] = _utc(end)
        # Keep the room's scheduling metadata in step, or the Meetings tab goes
        # on showing the old time next to the calendar's new one.
        room_id = event.get("video_room_id")
        if room_id:
            try:
                rows = c.get(f"/api/v1/data/{ROOMS}", params={"id": f"eq.{room_id}"})
                rows = rows if isinstance(rows, list) else ([rows] if rows else [])
                existing = rows[0].get("metadata") if rows else None
                metadata = dict(existing) if isinstance(existing, dict) else {}
                metadata["scheduledStartDate"] = _utc(start)
                metadata["scheduledEndDate"] = _utc(end)
                if "title" in patch:
                    metadata["calendarEventTitle"] = patch["title"]
                c.patch(f"/api/v1/data/{ROOMS}", params={"id": f"eq.{room_id}"},
                        json={"metadata": metadata})
            except Exception:
                pass

    if not patch:
        raise click.UsageError("nothing to update — pass at least one field.")

    result = c.patch(f"/api/v1/data/{EVENTS}", params={"id": f"eq.{event_id}"}, json=patch)
    _assert_changed(result, event_id, "update")
    click.echo("updated — note that a reschedule notifies nobody.", err=True)
    show(obj, result)


@calendar_group.command("delete", help="Cancel a meeting you created.")
@click.argument("event_id")
@click.option("--keep-room", is_flag=True, default=False,
              help="Leave the video room in place instead of deactivating it.")
@click.pass_obj
def calendar_delete(obj, event_id, keep_room):
    """Deletes the calendar entry and, unless told otherwise, deactivates the
    room behind it — a room left active outlives the meeting and keeps showing
    up in the Meetings tab as something people can still join.

    Cancellation notifies nobody either."""
    c = client(obj)
    event = _get_event(c, event_id)
    result = c.delete(f"/api/v1/data/{EVENTS}", params={"id": f"eq.{event_id}"})
    _assert_changed(result, event_id, "delete")

    room_id = event.get("video_room_id")
    if room_id and not keep_room:
        try:
            c.patch(f"/api/v1/data/{ROOMS}", params={"id": f"eq.{room_id}"},
                    json={"is_active": False})
        except Exception:
            click.echo(f"note: the calendar entry is gone but room {room_id} "
                       "could not be deactivated.", err=True)
    click.echo("cancelled — note that attendees are not notified.", err=True)
    show(obj, result)
