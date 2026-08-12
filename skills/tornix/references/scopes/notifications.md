# `tornix api notifications` — 22 commands

- `tornix api notifications credit-alert --json` — Internal: fan-out low-credit alert to Telegram + Email
- `tornix api notifications delete --json` — NotificationsController_delete
- `tornix api notifications expo-push-token --json` — Register Expo push token
- `tornix api notifications expo-push-token-delete --json` — Unregister Expo push token
- `tornix api notifications get --json` — List Expo push tokens for a user
- `tornix api notifications link --json` — Start Telegram linking flow
- `tornix api notifications list --json` — NotificationsController_findAll
- `tornix api notifications push-subscribe --json` — Register push subscription
- `tornix api notifications push-subscribe-delete --json` — Unregister push subscription
- `tornix api notifications read --json` — NotificationsController_markRead
- `tornix api notifications read-all --json` — NotificationsController_markAllRead
- `tornix api notifications send-push --json` — Trigger Expo push + Socket.io for a DB notification
- `tornix api notifications settings --json` — Get Telegram notification settings for the current user
- `tornix api notifications status --json` — Poll Telegram linking status
- `tornix api notifications telegram-link-delete --json` — Unlink Telegram (clear chat_id)
- `tornix api notifications telegram-settings-replace --json` — Update Telegram notification settings
- `tornix api notifications test --json` — Send a test message to verify Telegram connection
- `tornix api notifications test-expo-push --json` — Test Expo push notification to a user
- `tornix api notifications unread-count --json` — Unread notification count (optionally org/category-scoped)
- `tornix api notifications voip-push-token --json` — Register VoIP push token (iOS PushKit)
- `tornix api notifications voip-push-token-delete --json` — Unregister VoIP push token
- `tornix api notifications web-push --json` — Send web push notification to user

(22 commands)
