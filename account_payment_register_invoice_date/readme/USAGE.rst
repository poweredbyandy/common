Install the module and register a grouped payment for several customer or vendor
invoices as usual.

When the payment amount does not cover every selected invoice, the
reconciliation applies funds starting with the earliest ``invoice_date`` (or
accounting date when the invoice date is empty). Invoices of the same day are
ordered by ``l10n_ve_invoice_date`` when that field exists, otherwise by
``create_date``.
