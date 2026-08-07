Usage
=====

1. Configure Meta App credentials in *WhatsApp → Settings*:

   * Choose **Active Meta App**: Test App or Production App
   * Fill credentials for each environment (different App IDs):

     * Test: App ID, App Secret, Embedded Signup Configuration ID
     * Production: App ID, App Secret, Embedded Signup Configuration ID

   * Graph API version
   * Webhook verify token

   Odoo uses only the active environment for Embedded Signup / token
   exchange. Webhook and Facebook callbacks accept signatures from both
   Test and Production secrets when configured.

   Paste the legal URLs from Settings into Meta App Dashboard →
   *Settings → Basic*:

   * Terms of Service URL → ``/mail_whatsapp/legal/terms`` (required for Live)
   * Privacy Policy URL → ``/mail_whatsapp/legal/privacy`` (required; must
     explain data use and deletion; public and crawlable)
   * User data deletion → instructions URL
     ``/mail_whatsapp/legal/data-deletion`` and/or the Data Deletion Callback

2. In the Meta App Dashboard, set the webhook callback URL to the value shown
   on the WhatsApp account form (``/mail_whatsapp/webhook``) and subscribe to:

   * ``messages``
   * ``history``
   * ``smb_app_state_sync``
   * ``smb_message_echoes``
   * ``account_update``

3. Open *WhatsApp → Connect with Embedded Signup* and follow progressive
   Facebook Login permissions:

   * Step 1: grant classic scopes ``public_profile`` and ``email`` (Login
     Button / Request login permissions).
   * Review ``/me/permissions``. If the user declined a permission, show why
     it is needed and use **Re-ask declined permissions** once
     (``auth_type: rerequest``). Without that flag the Login Dialog will not
     ask again.
   * Step 2: **Continue with Facebook (Coexistence)** launches Embedded Signup
     (``config_id`` + ``featureType: whatsapp_business_app_onboarding``) for
     WhatsApp business permissions. Do not request those in the same dialog as
     the basic login scopes.

   Permissions beyond default fields + ``email`` require Meta App Review before
   general public use.

4. Complete the Meta flow selecting the option to connect an existing WhatsApp
   Business App number (Coexistence). Keep the WhatsApp Business App open while
   contacts and history sync (must finish within 24 hours).

5. Incoming messages and messages sent from the Business App appear in
   **Discuss → WhatsApp** (dedicated sidebar category). Notify users configured
   on the WhatsApp account become channel members. Each chat can show tags next
   to its name (sidebar and header). The first automatic tag is the Odoo user
   who last replied (``Replied: Name``). Use **Edit Contact** in the chat
   header to rename the WhatsApp contact in a modal (the chat title updates
   accordingly), and **Add Tags** to assign custom tags (also under
   *WhatsApp → Tags*). Replies from Discuss are sent through Cloud API when
   the 24-hour customer service window is active. In Demo mode, use
   *Simulate Incoming Message* and then open Discuss to see the conversation
   under WhatsApp.

6. **24-hour customer service window**: when the customer sends a message, a
   24-hour window opens. During that window you can reply with free text from
   Discuss or from the document chatter (WhatsApp button → message field).
   When the window is closed, Discuss blocks free-text replies and the chatter
   composer requires an approved template. Create and approve templates under
   *WhatsApp → Templates* (Demo auto-approves on submit).

7. From any document chatter (Contacts, Sales, etc.), use the **WhatsApp**
   button (green icon) next to Log note. This opens the WhatsApp composer
   inline in the chatter (no popup). If the 24-hour window is open, write a
   free-text message; otherwise select an approved template, then send. The
   message is logged on the chatter and mirrored in Discuss with a link to
   the document.

8. In Meta App Dashboard configure Facebook Login callbacks shown in
   *WhatsApp → Settings*:

   * **Data deletion request URL** (*Settings → Basic*):
     ``/mail_whatsapp/facebook/data_deletion`` — returns JSON
     ``{url, confirmation_code}`` and processes deletion.
   * **Deauthorize Callback URL** (*Settings → Advanced*):
     ``/mail_whatsapp/facebook/deauthorize`` — notified when a user removes
     the app; Odoo clears tokens and deactivates linked accounts.

   Browser Facebook Login tokens are short-lived; the server exchanges the
   Embedded Signup ``code`` for a token, re-verifies it with Graph
   ``debug_token`` (app_id / user_id), and upgrades to a long-lived token
   when Meta allows it. Document data deletion in your Privacy Policy.

WhatsApp follow-up automation
-----------------------------

Any model with ``mail.activity.mixin`` can call
``action_whatsapp_schedule_followup()`` to open the shared wizard
(``mail.whatsapp.followup``).

Override these hooks in your module as needed:

* ``_whatsapp_followup_get_interest`` / ``_whatsapp_followup_set_interest``
* ``_whatsapp_followup_get_contact_name``
* ``_whatsapp_followup_default_activity_type``
* ``_get_whatsapp_followup_message``
