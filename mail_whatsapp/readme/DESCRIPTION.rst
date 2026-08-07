Mail WhatsApp
=============

Integrates Odoo with the WhatsApp Cloud API using Meta **Coexistence**
(WhatsApp Business App + Cloud API on the same phone number).

Onboarding uses the official Meta **Embedded Signup** OAuth flow with
``featureType: whatsapp_business_app_onboarding``.

Features
--------

* WhatsApp Business Account creation via Embedded Signup
* Webhook handling for inbound messages, delivery statuses,
  ``smb_message_echoes``, chat ``history`` sync and ``smb_app_state_sync``
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
