Allows regenerating missing journal entries on payments that were confirmed
while the bank or cash journal had no outstanding payments/receipts account
configured on its payment method lines.

Without that account, Odoo creates the payment without an ``account.move``.
After the accounts are set, this module provides a button (and a list action)
to create the entry, post it and reconcile it with the linked invoices.

It also shows the bank reconciliation setup status on bank and cash journals
(form smart button and list badge) and opens a wizard to enable or disable it:

* Enable: create/reuse Outstanding Receipts/Payments accounts named after the
  journal account and assign them to payment methods
* Disable: set payment methods to the journal account

Adds a menu entry for Account Groups under Accounting configuration, right
after the Chart of Accounts, and a custom OWL left panel on the chart of
accounts that lists:

* account groups as ``CODE Group Name``
* ungrouped accounts as ``CODE Ungrouped`` with a **Create Group** button

