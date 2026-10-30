=============
Mail WhatsApp
=============

.. contents::
   :local:

Description
===========

Integrates Odoo with WhatsApp using Manual Cloud API, Meta Embedded Signup
(Coexistence) or Dualhook (``dh_live_`` Runtime API + Webhook Override).

Includes Meta privacy/login callbacks:

* **Data Deletion Request Callback**: validates ``signed_request``, deletes
  Facebook-linked WhatsApp credentials, returns ``{url, confirmation_code}``.
* **Deauthorize Callback**: clears tokens when a user removes the app.
* Server-side ``debug_token`` verification and long-lived token exchange.
* Progressive Login permissions, ``/me/permissions`` checks, and
  ``auth_type: rerequest`` for declined scopes.

WhatsApp chats live in their own app (*WhatsApp → Chats*), out of Discuss,
with four access levels, per-account agents and a responsible per chat.

Configuration
=============

In *Settings → Users*, the **WhatsApp** field has four levels:

* **User: Own Chats Only**: chats assigned to the user and unassigned chats.
* **User: All Chats**: every chat of the user's accounts.
* **Account Administrator**: edits the accounts where they are Account
  Administrator (agents, templates, tags) and assigns their chats.
* **Administrator**: every account, Meta connection, settings, simulator and
  data deletion requests.

On the account, tab **Team**, add the users to **Agents** or **Account
Administrators**. Users only see the chats, messages and templates of their
accounts. Notify users are added to Agents automatically.

Usage
=====

1. Configure Meta App credentials in *WhatsApp → Configuration → Settings*:

   * Select **Active Meta App** (Test or Production)
   * Enter separate App ID / App Secret / Embedded Signup Config ID
     for Test and Production
   * Graph API version
   * Webhook Verify Token

   Or create the account with *Setup = Dualhook* and paste the ``dh_live_``
   key after connecting the WABA in Dualhook.

2. In the Meta App Dashboard, set the webhook callback URL shown on the
   WhatsApp account form (``/mail_whatsapp/webhook``) and subscribe to:

   * ``messages``
   * ``history``
   * ``message_echoes`` (Cloud API)
   * ``smb_message_echoes`` (WhatsApp Business)
   * ``smb_app_state_sync``
   * ``account_update``

3. In Meta App Dashboard, paste the callback URLs from *WhatsApp → Configuration → Settings*:

   * Data deletion request URL → ``/mail_whatsapp/facebook/data_deletion``
   * Deauthorize Callback URL → ``/mail_whatsapp/facebook/deauthorize``

   Document the deletion process in your Privacy Policy.

4. Open *WhatsApp → Configuration → Connect Meta Account* and complete the Meta flow
   selecting the option to connect an existing WhatsApp Business App number.

5. Keep the WhatsApp Business App open while contacts and history sync
   (must finish within 24 hours after onboarding).

6. Conversations appear in *WhatsApp → Chats*, not in Discuss; the messaging
   menu still notifies and opens them there. Replies are sent through Cloud
   API while the 24-hour customer service window is active, and outgoing
   messages are labelled **API** or **WhatsApp Business**. The first agent who
   answers an unassigned chat becomes its responsible; use **Responsible** in
   the chat header to take, release or (Account Administrators) reassign it.
   Filter the list with **My chats** and **Unassigned**.

7. *WhatsApp → Reporting → Dashboard* counts messages sent from Odoo and replies sent
   from the phone (WhatsApp Business). Response time uses whichever reply
   came first. The history import is excluded, and phone replies are not
   assigned to an agent in Top Writers.

Contributors
============

* andyengit
