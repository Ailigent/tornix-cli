# `tornix api storage` — 14 commands

- `tornix api storage abort --json` — Abort a multipart upload
- `tornix api storage complete --json` — Complete a multipart upload
- `tornix api storage copy --json` — Copy a file within a bucket
- `tornix api storage create --json` — Initiate a multipart upload
- `tornix api storage delete --json` — Delete a single file
- `tornix api storage download --json` — Download a file as a blob
- `tornix api storage files --json` — Bulk delete files
- `tornix api storage list --json` — List files in a bucket/folder (scoped to one of the caller's projects)
- `tornix api storage media-token --json` — Mint a short-lived signed token for GET /storage/public/:bucket/*
- `tornix api storage part-urls --json` — Get presigned URLs for a batch of parts
- `tornix api storage public --json` — Serve a public file by streaming from S3
- `tornix api storage signed-url --json` — Get signed download URL
- `tornix api storage upload --json` — Get presigned upload URL
- `tornix api storage upload-direct --json` — Upload file directly through backend (avoids S3 CORS)

(14 commands)
