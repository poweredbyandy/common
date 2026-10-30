Configure
=========

Access levels
-------------

In *Settings → Users*, the **WhatsApp** field has four levels:

* **User: Own Chats Only**: chats assigned to the user and unassigned chats.
* **User: All Chats**: every chat of the user's accounts.
* **Account Administrator**: edits the accounts where they are Account
  Administrator (agents, templates, tags) and assigns their chats.
* **Administrator**: every account, Meta connection, settings, simulator and
  data deletion requests.

Then open the account, tab **Team**, and add the users to **Agents** or
**Account Administrators** (only Administrators change the latter). Users only
see the chats, messages and templates of the accounts where they are listed.
Notify users are added to Agents automatically.

Meta Cloud API / Embedded Signup
--------------------------------

Set Test and Production App ID, App Secret and Embedded Signup Configuration
ID in *WhatsApp → Configuration → Settings*. Choose the active Meta App environment.

Dualhook
--------

No Meta App credentials are required on the Dualhook account. In Dualhook:

1. Create a connection and enter the Odoo webhook URL
   (``/mail_whatsapp/webhook``) plus the verify token shown on the account.
2. Complete Dualhook Embedded Signup.
3. Copy WABA ID, Phone Number ID and the ``dh_live_`` outbound key into the
   Odoo WhatsApp account with *Setup = Dualhook*.
