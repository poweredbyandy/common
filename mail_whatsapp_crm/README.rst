==================
Mail WhatsApp CRM
==================

.. |badge1| image:: https://img.shields.io/badge/licence-LGPL--3-blue.png
    :target: http://www.gnu.org/licenses/lgpl-3.0-standalone.html
    :alt: License: LGPL-3

|badge1|

Create CRM leads from WhatsApp Discuss chats and schedule interest-based follow-ups.

**Table of contents**

.. contents::
   :local:

Description
===========

This module connects WhatsApp Discuss conversations with CRM.

* Create a CRM lead/opportunity from a WhatsApp chat with one click
* Prefill contact data and assign medium **WhatsApp** plus CRM tag **WhatsApp**
* Capture what the contact was interested in (**Intereses**)
* Schedule a follow-up activity in X days with an effective personalized message

Use Cases / Context
===================

WhatsApp often starts commercial conversations before a formal CRM record exists.
Sales teams need a fast path from chat to opportunity, with the WhatsApp channel
as medium/tag, and a lightweight follow-up based on the contact's stated interest.

Usage
=====

Create a CRM lead from WhatsApp
-------------------------------

#. Open **Discuss** and select a WhatsApp conversation (WhatsApp Focus).
#. Click the **Create CRM** button (next to Edit Contact).
#. The lead is created with contact data, medium **WhatsApp** and tag **WhatsApp**.
#. Complete **Intereses** with what the person asked about, then save.

Schedule an interest follow-up
------------------------------

#. Open the CRM lead/opportunity.
#. Fill the **Intereses** field on the **WhatsApp** tab (if not already set).
#. Click **WhatsApp Follow-up** in the header.
#. Choose in how many days to follow up (default: 3).
#. Review/edit the suggested message and confirm **Schedule Follow-up**.

Suggested message (editable)::

    Hola {nombre},

    Nos escribiste por WhatsApp porque querías saber acerca de: {intereses}.

    ¿Sigues interesado/a? Si quieres, te ayudo a retomar el tema y te
    comparto la información actualizada para que tomes una decisión con claridad.

    ¿Te viene bien que conversemos hoy o mañana?

    Quedo atento/a a tu respuesta.

The activity type **WhatsApp Interest Follow-up** also links the email template
for sending from the activity when useful.

Bug Tracker
===========

Bugs are tracked on GitHub Issues. In case of trouble, please check there.

Credits
=======

Authors
-------

* andyengit

Contributors
------------

* andyengit

Maintainers
-----------

This module is maintained by andyengit.
