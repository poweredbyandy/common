Venezuelan banks (BNC, Banesco, Mercantil, Provincial, ...) export mobile
payment (Pago Móvil) statements without the customer, only with the operation
reference. Cashiers register each payment in Odoo with that same reference,
sometimes shortened or with leading zeros.

The standard Enterprise rules need a partner on the statement line, so those
payments are never matched automatically. This module matches them by
reference instead.

It is the Enterprise counterpart of the OCA module
`l10n_ve_bank_reconcile_ref`, which depends on `account_reconcile_model_oca`
and cannot be installed with `account_accountant`.
