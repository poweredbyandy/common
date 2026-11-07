================
Mail Gmail User
================

Connect each internal user's Gmail account to Odoo for outgoing mail and
related incoming replies.

**Table of contents**

.. contents::
   :local:

Description
===========

Connect each internal user's Gmail account to Odoo for outgoing mail and related
incoming replies.

The company keeps a general outgoing mail server. When a user connects Gmail,
their messages leave as that user's address. A systray indicator shows whether
the account is connected.

Use Cases / Context
===================

Sales and support teams often need to write customers from their own mailbox
while still working inside Odoo.

Configuration
=============

* Create a Google OAuth web client with redirect
  ``{web.base.url}/mail_gmail_user/confirm``.
* Set Client ID / Secret in Odoo Settings.
* Configure the company email and general outgoing mail server.

Usage
=====

* Connect Gmail from the systray envelope icon.
* Green means connected; red means the user must sign in.
* Disconnected users confirm before sending as the company account.
* Administrators review accounts under Settings > Users & Companies > Gmail Accounts.

Contributors
============

* andyengit
