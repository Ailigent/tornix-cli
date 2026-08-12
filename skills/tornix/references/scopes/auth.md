# `tornix api auth` — 26 commands

- `tornix api auth check-email --json` — Check if an email address is already registered
- `tornix api auth check-email-confirmed --json` — Check if an email address has been confirmed
- `tornix api auth confirm-email --json` — Confirm email address via token link
- `tornix api auth create-user-with-password --json` — Create a new user with email/password (admin invitation)
- `tornix api auth delete --json` — Turn biometric sign-in off for one enrolled device
- `tornix api auth enroll --json` — Enroll this device for biometric sign-in; returns its token once
- `tornix api auth exchange --json` — Trade an enrolled device token for a session
- `tornix api auth google --json` — Initiate Google OAuth login — redirects to Google
- `tornix api auth login --json` — Login with email and password
- `tornix api auth logout --json` — Log out and invalidate refresh token
- `tornix api auth me --json` — Get current user info
- `tornix api auth me-replace --json` — Update current user (password, email, metadata)
- `tornix api auth otp-send-create --json` — Send OTP to email or phone
- `tornix api auth otp-verify-create --json` — Verify OTP code
- `tornix api auth refresh --json` — Refresh JWT token using refresh_token
- `tornix api auth register --json` — Register a new user with email and password
- `tornix api auth reset-password --json` — Send password reset email via Brevo
- `tornix api auth revoke --json` — Retire an enrolled device token
- `tornix api auth send --json` — Resend the email/SMS 2FA code during the login pending window
- `tornix api auth send-confirmation --json` — Send email confirmation link via Brevo
- `tornix api auth send-sms --json` — Send OTP via SMS (Brevo)
- `tornix api auth setup --json` — Set up TOTP (Google Authenticator) - generates secret and QR URI
- `tornix api auth totp-verify-create --json` — Verify TOTP code from authenticator app
- `tornix api auth update-password --json` — Set a new password using a reset token
- `tornix api auth verify --json` — Complete login for a 2FA-enabled account (pending_token + code)
- `tornix api auth verify-password --json` — Verify user password without creating a session

(26 commands)
