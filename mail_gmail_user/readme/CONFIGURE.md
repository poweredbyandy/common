1. In Google Cloud, create an OAuth client for a web application.
2. Add the redirect URI ``{web.base.url}/google_gmail/confirm`` (same as native Gmail).
3. Use scope ``https://mail.google.com/`` on an internal Workspace consent screen.
4. In Odoo **Settings > Discuss**, set the Gmail Client ID and Client Secret.
5. Configure the company email and a general outgoing mail server for company
   fallback.
