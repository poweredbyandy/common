================
Res Users User
================

.. contents::
   :local:

Description
===========

This module allows several sellers (sub-users) to share the same Odoo user
while keeping an audit trail of who performed each action.

Each sub-user is linked to an ``hr.employee`` and authenticates with the
employee PIN, similar to the POS cashier switch. A lock action closes the
sub-user session without logging out the Odoo user.

Traceability is generic: create/write actions are logged and chatter
messages show the active sub-user. Access rights and record visibility
remain those of the parent Odoo user.

Use Cases / Context
===================

In shops or counters several people often share one Odoo login for
operational convenience. Without a sub-user concept it is impossible to
know which seller created or updated a document.

This module covers that business need by introducing selectable
sub-users under a shared user, with PIN-based lock/switch and cross-model
traceability.

Configuration
=============

#. Open **Settings > Users & Companies > Users** and select the shared
   user.
#. Enable **Require Sub-User** if the session must always have an active
   sub-user.
#. In the **Sub-Users** tab, add lines with an employee.
#. Set a numeric PIN on each employee (HR employee form or related PIN
   field on the sub-user line).
#. Each employee can be linked to several parent users if needed, but
   the pair user/employee must be unique.

Usage
=====

#. Log in with the shared Odoo user.
#. If sub-users are configured, the lock screen asks you to select a
   sub-user and enter its PIN.
#. The active sub-user appears in the navbar systray.
#. Use the lock icon to close the sub-user session without logging out
   of Odoo; another seller can then select their sub-user with PIN.
#. Chatter messages and the sub-user audit log record which sub-user
   performed create/write actions.

Authors
=======

* andyengit

Contributors
============

* andyengit
