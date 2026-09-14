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

Usage
=====

1. Configure Meta App credentials in *WhatsApp → Settings*:

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

3. In Meta App Dashboard, paste the callback URLs from *WhatsApp → Settings*:

   * Data deletion request URL → ``/mail_whatsapp/facebook/data_deletion``
   * Deauthorize Callback URL → ``/mail_whatsapp/facebook/deauthorize``

   Document the deletion process in your Privacy Policy.

4. Open *WhatsApp → Connect with Embedded Signup* and complete the Meta flow
   selecting the option to connect an existing WhatsApp Business App number.

5. Keep the WhatsApp Business App open while contacts and history sync
   (must finish within 24 hours after onboarding).

6. Conversations appear in Discuss WhatsApp channels. Replies from Discuss are
   sent through Cloud API while the 24-hour customer service window is active.
   Discuss labels outgoing messages as **API** or **WhatsApp Business**.

Contributors
============

* andyengit
