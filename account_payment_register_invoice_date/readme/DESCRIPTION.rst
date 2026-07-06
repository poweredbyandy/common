When registering a grouped payment for several invoices, Odoo does not guarantee
that the payment amount is applied from the oldest invoice to the newest.

This module reconciles grouped payments using the invoice date, from oldest to
newest. Partial payments therefore close older invoices first before affecting
newer ones.
