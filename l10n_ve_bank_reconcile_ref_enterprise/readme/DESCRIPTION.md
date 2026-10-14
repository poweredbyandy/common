Automatic bank reconciliation by bank reference for Odoo Enterprise.

Adds a step to the *Invoice Matching* reconciliation models: the bank
reference of the statement line is compared with the reference of open
payments (memo) and invoices. It tries the full reference first, then its last
digits (6 then 4 by default). Leading zeros are ignored.

A line is validated automatically only when there is a single candidate and
the amount matches. Otherwise the candidates are only suggested.

Statements imported with the OCA file import wizard are reconciled right after
the import, like the Enterprise import does.
