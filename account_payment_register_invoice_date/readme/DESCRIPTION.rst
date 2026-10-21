When registering a grouped payment for several invoices, Odoo does not guarantee
that the payment amount is applied from the oldest invoice to the newest.

This module reconciles grouped payments from the oldest document to the newest.
It uses the invoice date and, when several invoices share the same day, the
document datetime (or the creation time) so invoices that differ only by minutes
are paid in chronological order. Partial payments therefore close older invoices
first before affecting newer ones.
