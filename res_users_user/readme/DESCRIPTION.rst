This module allows several sellers (sub-users) to share the same Odoo user
while keeping an audit trail of who performed each action.

Each sub-user is linked to an ``hr.employee`` and authenticates with the
employee PIN, similar to the POS cashier switch. A lock action closes the
sub-user session without logging out the Odoo user.

Traceability is generic: create/write actions are logged and chatter
messages show the active sub-user. Access rights and record visibility
remain those of the parent Odoo user.
