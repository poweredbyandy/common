Configure
=========

Meta Cloud API / Embedded Signup
--------------------------------

Set Test and Production App ID, App Secret and Embedded Signup Configuration
ID in *WhatsApp → Settings*. Choose the active Meta App environment.

Dualhook
--------

No Meta App credentials are required on the Dualhook account. In Dualhook:

1. Create a connection and enter the Odoo webhook URL
   (``/mail_whatsapp/webhook``) plus the verify token shown on the account.
2. Complete Dualhook Embedded Signup.
3. Copy WABA ID, Phone Number ID and the ``dh_live_`` outbound key into the
   Odoo WhatsApp account with *Setup = Dualhook*.
