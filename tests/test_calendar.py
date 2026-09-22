"""`tornix calendar` — the meeting surface.

These tests exist because the bug they guard against was invisible: the old
`meetings room-create` wrote a row, exited 0, and produced a meeting that was
on nobody's calendar and that nobody had been invited to. Every assertion below
is about a specific way that can happen again.
"""
import json

import httpx
from click.testing import CliRunner

from tornix_cli.client import TornixClient
from tornix_cli.commands.calendar import calendar_group
from tornix_cli.config import Config

ORG = "11111111-1111-1111-1111-111111111111"
ME = "22222222-2222-2222-2222-222222222222"
AHMED = "33333333-3333-3333-3333-333333333333"
SARA = "44444444-4444-4444-4444-444444444444"
EVENT = "55555555-5555-5555-5555-555555555555"
ROOM = "66666666-6666-6666-6666-666666666666"

MEMBERS = [
    {"user_id": ME, "user": {"id": ME, "email": "me@tornix.ai",
                             "profile": {"full_name": "Me Myself"}}},
    {"user_id": AHMED, "user": {"id": AHMED, "email": "ahmed@tornix.ai",
                                "profile": {"full_name": "Ahmed Ibrahim"}}},
    {"user_id": SARA, "user": {"id": SARA, "email": "sara@tornix.ai",
                               "profile": {"full_name": "Sara Ahmed"}}},
]


def _obj(handler):
    cfg = Config(api_url="https://x.test", api_key="tk", org_id=ORG)
    return {"config": cfg,
            "client": TornixClient(cfg, transport=httpx.MockTransport(handler)),
            "json": True}


def _recorder(*, event_row=None, room_row=None, events_on_get=None):
    """A mock backend that records every call and answers the four routes the
    calendar commands use."""
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content) if req.content else None
        calls.append({"method": req.method, "path": req.url.path,
                      "query": dict(req.url.params), "body": body})
        path = req.url.path
        if path.endswith("/members"):
            return httpx.Response(200, json=MEMBERS)
        if path == "/api/v1/users/me":
            return httpx.Response(200, json={"id": ME, "email": "me@tornix.ai"})
        if path == "/api/v1/data/video_rooms":
            if req.method == "GET":
                return httpx.Response(200, json=[room_row or {"id": ROOM, "metadata": {}}])
            return httpx.Response(200, json={"id": ROOM})
        if path == "/api/v1/data/calendar_events":
            if req.method == "GET":
                return httpx.Response(200, json=events_on_get
                                      if events_on_get is not None
                                      else [event_row or {"id": EVENT}])
            if req.method in ("PATCH", "DELETE"):
                return httpx.Response(200, json={"id": EVENT, **(body or {})})
            return httpx.Response(200, json={"id": EVENT, **(body or {})})
        if path == "/api/v1/calendar/my-events":
            return httpx.Response(200, json=[])
        return httpx.Response(404, json={"message": f"unexpected {req.method} {path}"})

    return handler, calls


def _run(args, handler):
    return CliRunner().invoke(calendar_group, args, obj=_obj(handler))


# ── create ────────────────────────────────────────────────────────────────


def test_create_writes_both_the_room_and_the_calendar_entry():
    """The whole point: a meeting is a `video_rooms` row AND a `calendar_events`
    row. Writing only the room is the bug this command replaces."""
    handler, calls = _recorder()
    r = _run(["create", "--title", "Kickoff", "--start", "2099-10-01T14:00:00Z",
              "--attendee", "ahmed@tornix.ai"], handler)
    assert r.exit_code == 0, r.output

    writes = [c for c in calls if c["method"] == "POST"]
    assert [w["path"] for w in writes] == [
        "/api/v1/data/video_rooms", "/api/v1/data/calendar_events"
    ], "the room must be written BEFORE the event that links and announces it"


def test_create_stamps_user_id_because_the_proxy_does_not():
    """`calendar_events.user_id` is NOT NULL and the data proxy does not fill it
    on insert — an omitted creator is a hard insert failure."""
    handler, calls = _recorder()
    assert _run(["create", "--title", "X", "--start", "2099-10-01T14:00:00Z"],
                handler).exit_code == 0
    event = [c for c in calls if c["path"].endswith("calendar_events")][0]
    assert event["body"]["user_id"] == ME


def test_create_puts_the_attendee_in_participants_which_is_the_invitation():
    """The proxy's INSERT hook notifies every participant carrying an `id`; a
    participant without one is silently skipped by the notifier."""
    handler, calls = _recorder()
    assert _run(["create", "--title", "X", "--start", "2099-10-01T14:00:00Z",
                 "--attendee", "ahmed@tornix.ai"], handler).exit_code == 0
    event = [c for c in calls if c["path"].endswith("calendar_events")][0]
    assert event["body"]["participants"] == [{
        "id": AHMED, "name": "Ahmed Ibrahim", "email": "ahmed@tornix.ai",
        "responseStatus": "needsAction",
    }]


def test_create_marks_the_room_as_scheduled():
    """Without `metadata.scheduledStartDate` the Meetings tab renders the room
    as an ad-hoc quick room — no time, no attendees, no edit-as-meeting."""
    handler, calls = _recorder()
    assert _run(["create", "--title", "Kickoff", "--start", "2099-10-01T14:00:00Z",
                 "--duration", "30", "--attendee", "ahmed@tornix.ai"],
                handler).exit_code == 0
    room = [c for c in calls if c["path"].endswith("video_rooms")][0]
    meta = room["body"]["metadata"]
    assert meta["scheduledStartDate"] == "2099-10-01T14:00:00.000Z"
    assert meta["scheduledEndDate"] == "2099-10-01T14:30:00.000Z"
    assert meta["calendarEventTitle"] == "Kickoff"
    # The ROOM's shape uses `fullName`; the CALENDAR's uses `name`. They differ.
    assert meta["invitedParticipants"] == [
        {"id": AHMED, "email": "ahmed@tornix.ai", "fullName": "Ahmed Ibrahim"}
    ]


def test_create_links_the_room_to_the_event_and_builds_a_join_link():
    handler, calls = _recorder()
    assert _run(["create", "--title", "X", "--start", "2099-10-01T14:00:00Z"],
                handler).exit_code == 0
    event = [c for c in calls if c["path"].endswith("calendar_events")][0]
    assert event["body"]["video_room_id"] == ROOM
    assert event["body"]["meeting_link"] == f"https://x.test/dashboard/meetings/{ROOM}"


def test_no_video_books_time_only():
    handler, calls = _recorder()
    assert _run(["create", "--title", "Focus", "--start", "2099-10-01T14:00:00Z",
                 "--no-video"], handler).exit_code == 0
    assert not [c for c in calls if c["path"].endswith("video_rooms")]
    event = [c for c in calls if c["path"].endswith("calendar_events")][0]
    assert event["body"]["video_room_id"] is None


def test_unknown_attendee_aborts_before_anything_is_written():
    """Resolution happens first on purpose: a half-built meeting with a missing
    invitee is the same failure in a smaller box."""
    handler, calls = _recorder()
    r = _run(["create", "--title", "X", "--start", "2099-10-01T14:00:00Z",
              "--attendee", "nobody@example.com"], handler)
    assert r.exit_code != 0
    assert "matched nobody" in r.output
    assert not [c for c in calls if c["method"] == "POST"]


def test_ambiguous_name_is_refused_rather_than_guessed():
    """'Ahmed' is both Ahmed Ibrahim and Sara Ahmed — inviting the wrong person
    is worse than asking."""
    handler, _ = _recorder()
    r = _run(["create", "--title", "X", "--start", "2099-10-01T14:00:00Z",
              "--attendee", "Ahmed"], handler)
    assert r.exit_code != 0
    assert "matches 2 people" in r.output


def test_attendee_resolves_by_exact_name():
    handler, calls = _recorder()
    assert _run(["create", "--title", "X", "--start", "2099-10-01T14:00:00Z",
                 "--attendee", "Sara Ahmed"], handler).exit_code == 0
    event = [c for c in calls if c["path"].endswith("calendar_events")][0]
    assert [p["id"] for p in event["body"]["participants"]] == [SARA]


def test_duplicate_attendees_are_collapsed():
    handler, calls = _recorder()
    assert _run(["create", "--title", "X", "--start", "2099-10-01T14:00:00Z",
                 "--attendee", "ahmed@tornix.ai", "--attendee", AHMED],
                handler).exit_code == 0
    event = [c for c in calls if c["path"].endswith("calendar_events")][0]
    assert len(event["body"]["participants"]) == 1


def test_end_before_start_is_refused():
    handler, _ = _recorder()
    r = _run(["create", "--title", "X", "--start", "2099-10-01T14:00:00Z",
              "--end", "2099-10-01T13:00:00Z"], handler)
    assert r.exit_code != 0
    assert "--end must be after --start" in r.output


def test_all_day_spans_the_calendar_day():
    handler, calls = _recorder()
    assert _run(["create", "--title", "Leave", "--start", "2099-10-01T09:30:00Z",
                 "--all-day"], handler).exit_code == 0
    event = [c for c in calls if c["path"].endswith("calendar_events")][0]
    assert event["body"]["start_date"] == "2099-10-01T00:00:00.000Z"
    assert event["body"]["end_date"] == "2099-10-01T23:59:59.999Z"
    assert event["body"]["is_all_day"] is True


def test_a_naive_instant_is_read_as_utc_not_as_host_local_time():
    """The agent's container runs on UTC; guessing the host's offset would move
    every meeting the user books."""
    handler, calls = _recorder()
    assert _run(["create", "--title", "X", "--start", "2099-10-01 14:00"],
                handler).exit_code == 0
    event = [c for c in calls if c["path"].endswith("calendar_events")][0]
    assert event["body"]["start_date"] == "2099-10-01T14:00:00.000Z"


def test_a_past_meeting_warns_that_nobody_will_be_invited():
    """The notifier ignores meetings that have already ended, so a create that
    quietly invites nobody must say so."""
    handler, _ = _recorder()
    r = _run(["create", "--title", "X", "--start", "2000-01-01T10:00:00Z",
              "--attendee", "ahmed@tornix.ai"], handler)
    assert r.exit_code == 0, r.output
    assert "no invitations will be sent" in r.output


# ── invite / uninvite ─────────────────────────────────────────────────────


EXISTING = {"id": EVENT, "video_room_id": ROOM, "participants": [
    {"id": SARA, "name": "Sara Ahmed", "email": "sara@tornix.ai"}]}


def test_invite_merges_and_never_replaces():
    """`participants` is one JSON column — writing the new person alone would
    un-invite everybody already in the meeting."""
    handler, calls = _recorder(event_row=EXISTING)
    r = _run(["invite", EVENT, "--attendee", "ahmed@tornix.ai"], handler)
    assert r.exit_code == 0, r.output
    patch = [c for c in calls
             if c["method"] == "PATCH" and c["path"].endswith("calendar_events")][0]
    assert [p["id"] for p in patch["body"]["participants"]] == [SARA, AHMED]


def test_invite_goes_through_the_data_proxy_because_that_is_what_notifies():
    """`PATCH /calendar/events/{id}` is a direct Prisma update with no
    data-proxy event hook — adding an attendee through it is silent."""
    handler, calls = _recorder(event_row=EXISTING)
    assert _run(["invite", EVENT, "--attendee", "ahmed@tornix.ai"],
                handler).exit_code == 0
    assert not [c for c in calls if c["path"].startswith("/api/v1/calendar/events")]


def test_invite_also_updates_the_room_avatar_list_without_dropping_scheduling():
    handler, calls = _recorder(
        event_row=EXISTING,
        room_row={"id": ROOM, "metadata": {"scheduledStartDate": "2099-10-01T14:00:00.000Z"}},
    )
    assert _run(["invite", EVENT, "--attendee", "ahmed@tornix.ai"],
                handler).exit_code == 0
    room_patch = [c for c in calls
                  if c["method"] == "PATCH" and c["path"].endswith("video_rooms")][0]
    meta = room_patch["body"]["metadata"]
    assert meta["scheduledStartDate"] == "2099-10-01T14:00:00.000Z", \
        "a blind metadata overwrite demotes the meeting to a quick room"
    assert [p["id"] for p in meta["invitedParticipants"]] == [SARA, AHMED]


def test_invite_on_somebody_elses_meeting_is_an_error_not_a_silent_no_op():
    """The proxy scopes this table by creator and answers a scoped-out filtered
    UPDATE with `{"count": 0}` — success-looking, and completely wrong."""
    calls = []

    def handler(req):
        body = json.loads(req.content) if req.content else None
        calls.append({"method": req.method, "path": req.url.path, "body": body})
        if req.url.path.endswith("/members"):
            return httpx.Response(200, json=MEMBERS)
        if req.url.path == "/api/v1/data/calendar_events":
            if req.method == "GET":
                return httpx.Response(200, json=[EXISTING])
            return httpx.Response(200, json={"count": 0})
        return httpx.Response(200, json={"id": ROOM, "metadata": {}})

    r = _run(["invite", EVENT, "--attendee", "ahmed@tornix.ai"], handler)
    assert r.exit_code != 0
    assert "changed nothing" in r.output


def test_inviting_somebody_already_in_the_meeting_writes_nothing():
    handler, calls = _recorder(event_row=EXISTING)
    r = _run(["invite", EVENT, "--attendee", "sara@tornix.ai"], handler)
    assert r.exit_code == 0, r.output
    assert "already in this meeting" in r.output
    assert not [c for c in calls if c["method"] == "PATCH"]


def test_a_meeting_that_is_not_yours_reports_the_creator_scope():
    handler, _ = _recorder(events_on_get=[])
    r = _run(["invite", EVENT, "--attendee", "ahmed@tornix.ai"], handler)
    assert r.exit_code != 0
    assert "scopes this table by creator" in r.output


def test_uninvite_drops_the_person_and_says_nobody_is_told():
    handler, calls = _recorder(event_row=EXISTING)
    r = _run(["uninvite", EVENT, "--attendee", "sara@tornix.ai"], handler)
    assert r.exit_code == 0, r.output
    patch = [c for c in calls
             if c["method"] == "PATCH" and c["path"].endswith("calendar_events")][0]
    assert patch["body"]["participants"] == []
    assert "nobody is notified of a removal" in r.output


# ── list / update / delete ────────────────────────────────────────────────


def test_list_reads_my_events_not_the_proxy():
    """The proxy scopes by CREATOR, so a meeting a colleague booked you into can
    never come back through it — which is the "I don't see it" complaint."""
    handler, calls = _recorder()
    assert _run(["list", "--from", "2099-10-01T00:00:00Z", "--days", "7"],
                handler).exit_code == 0
    get = calls[-1]
    assert get["path"] == "/api/v1/calendar/my-events"
    assert get["query"]["from"] == "2099-10-01T00:00:00.000Z"
    assert get["query"]["to"] == "2099-10-08T00:00:00.000Z"


def test_list_refuses_a_window_wider_than_the_route_allows():
    handler, _ = _recorder()
    r = _run(["list", "--from", "2099-01-01T00:00:00Z", "--days", "400"], handler)
    assert r.exit_code != 0
    assert "120 days or less" in r.output


def test_update_keeps_the_rooms_scheduling_metadata_in_step():
    handler, calls = _recorder(
        event_row={"id": EVENT, "video_room_id": ROOM,
                   "start_date": "2099-10-01T14:00:00Z",
                   "end_date": "2099-10-01T15:00:00Z"},
        room_row={"id": ROOM, "metadata": {"calendarEventTitle": "Old"}},
    )
    r = _run(["update", EVENT, "--start", "2099-10-02T09:00:00Z"], handler)
    assert r.exit_code == 0, r.output
    room_patch = [c for c in calls
                  if c["method"] == "PATCH" and c["path"].endswith("video_rooms")][0]
    assert room_patch["body"]["metadata"]["scheduledStartDate"] == "2099-10-02T09:00:00.000Z"
    assert "notifies nobody" in r.output


def test_postponing_a_meeting_carries_its_duration_with_it():
    """`--start` alone means "move it". Holding the old end would refuse every
    postponement past that end — which is most of them — and would quietly
    stretch the ones it did accept."""
    handler, calls = _recorder(
        event_row={"id": EVENT, "video_room_id": None,
                   "start_date": "2099-10-01T14:00:00Z",
                   "end_date": "2099-10-01T14:30:00Z"},
    )
    r = _run(["update", EVENT, "--start", "2099-10-05T09:00:00Z"], handler)
    assert r.exit_code == 0, r.output
    patch = [c for c in calls
             if c["method"] == "PATCH" and c["path"].endswith("calendar_events")][0]
    assert patch["body"]["start_date"] == "2099-10-05T09:00:00.000Z"
    assert patch["body"]["end_date"] == "2099-10-05T09:30:00.000Z"


def test_an_explicit_end_still_wins_over_the_old_duration():
    handler, calls = _recorder(
        event_row={"id": EVENT, "video_room_id": None,
                   "start_date": "2099-10-01T14:00:00Z",
                   "end_date": "2099-10-01T14:30:00Z"},
    )
    assert _run(["update", EVENT, "--start", "2099-10-05T09:00:00Z",
                 "--end", "2099-10-05T11:00:00Z"], handler).exit_code == 0
    patch = [c for c in calls
             if c["method"] == "PATCH" and c["path"].endswith("calendar_events")][0]
    assert patch["body"]["end_date"] == "2099-10-05T11:00:00.000Z"


def test_update_with_no_fields_is_refused():
    handler, _ = _recorder()
    r = _run(["update", EVENT], handler)
    assert r.exit_code != 0
    assert "nothing to update" in r.output


def test_delete_also_deactivates_the_room_behind_the_meeting():
    """A room left active outlives the cancelled meeting and goes on showing up
    in the Meetings tab as something people can still join."""
    handler, calls = _recorder(event_row={"id": EVENT, "video_room_id": ROOM})
    r = _run(["delete", EVENT], handler)
    assert r.exit_code == 0, r.output
    room_patch = [c for c in calls
                  if c["method"] == "PATCH" and c["path"].endswith("video_rooms")][0]
    assert room_patch["body"] == {"is_active": False}


def test_delete_can_keep_the_room():
    handler, calls = _recorder(event_row={"id": EVENT, "video_room_id": ROOM})
    assert _run(["delete", EVENT, "--keep-room"], handler).exit_code == 0
    assert not [c for c in calls if c["method"] == "PATCH"]


def test_members_lists_who_can_be_invited():
    handler, _ = _recorder()
    r = _run(["members", "--query", "ahmed@"], handler)
    assert r.exit_code == 0, r.output
    assert AHMED in r.output and SARA not in r.output
