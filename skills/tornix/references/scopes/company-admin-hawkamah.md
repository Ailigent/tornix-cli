# `tornix api company-admin-hawkamah` — 4 commands

- `tornix api company-admin-hawkamah attempts --json` — One member's per-attempt scores + previous (reset) sittings — headlines only, never the questions or answers from Hawkamah's report
- `tornix api company-admin-hawkamah reset-attempts --json` — [Super admin] Reopen a member's Hawkamah attempts (Hawkamah archives the old sitting; the employee starts again at attempt 1 with the same login)
- `tornix api company-admin-hawkamah roster --json` — This organization's members merged with their Hawkamah governance-exam status (not_started | registered | grading | completed), keyed on work e-mail
- `tornix api company-admin-hawkamah status --json` — Does this organization resolve a Hawkamah API key (DB override or env fallback), and does it verify

(4 commands)
