Mail WhatsApp
=============

Integrates Odoo with WhatsApp using one of three account setups:

* **Manual Cloud API** — paste WABA / phone / Meta token
* **Embedded Signup** — Meta OAuth with
  ``featureType: whatsapp_business_app_onboarding`` (Coexistence)
* **Dualhook** — connect the WABA in Dualhook, then send through
  ``https://api.dualhook.com/v25.0`` with a ``dh_live_`` key. Dualhook
  configures Webhook Override so Meta delivers inbound webhooks to Odoo.

Features
--------

* WhatsApp Business Account creation via Embedded Signup
* Webhook handling for inbound messages, delivery statuses,
  ``message_echoes`` (Cloud API), ``smb_message_echoes`` (WhatsApp
  Business app), chat ``history`` sync and ``smb_app_state_sync``
* Discuss and message list distinguish messages sent from Odoo / API
  versus WhatsApp Business (including edits and deletes from the app)
* Discuss channels (``channel_type = whatsapp``) mirroring 1:1 conversations
* Automatic contact and history synchronization after coexistence onboarding
* Meta **Data Deletion Request Callback** (``signed_request``) with public
  status URL and confirmation code
* Meta **Deauthorize Callback** when users uninstall the app from Facebook
* Server-side access token re-verification (``debug_token``) and long-lived
  token exchange for Embedded Signup
* Progressive Facebook Login permissions (``scope``), ``/me/permissions``
  status, declined-permission handling and ``auth_type: rerequest``
* Separate Meta **Test** and **Production** app credentials with an active
  environment switch
* Reusable **WhatsApp follow-up** automation (``mail.whatsapp.followup``) for
  any model with activities; other modules can adapt interest/topic and message
