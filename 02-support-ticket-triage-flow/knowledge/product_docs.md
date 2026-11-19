# Acme Analytics - product documentation

## API keys
Open Settings > Developer > API keys and press "Create key". Give it a name and a scope (read or read-write).
The key is shown only once, so copy it immediately. Send it in the `Authorization: Bearer <key>` header.
Free plans can create 2 keys, Pro plans 10, Enterprise plans unlimited. Revoke a key at any time from the same page.

## Exporting data
Dashboards can be exported as CSV or PDF from the "..." menu of a dashboard. CSV exports are limited to 100,000 rows.
Larger exports must use the API endpoint `GET /v1/exports`, which streams the data in pages.

## Resetting a password
On the sign-in page choose "Forgot password". A reset link is emailed and is valid for 30 minutes.
If SSO is enabled for your organisation, the password is managed by your identity provider.

## Inviting team members
Admins can invite members under Settings > Team. Pro plans include 5 seats, Enterprise plans are billed per seat.
