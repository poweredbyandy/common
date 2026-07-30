When payments exist without a journal entry:

#. Configure the outstanding payments/receipts accounts on the bank or cash
   journal payment method lines.
#. Open the payment form and click **Generate Journal Entry**, or select
   several payments in the list and use **Action > Generate Journal Entry**.
#. The module creates and posts the journal entry, then reconciles the
   counterpart lines with the invoices already linked to the payment.
#. The payment keeps (or recovers) its previous state (``in_process`` or
   ``paid``).

On bank and cash journals, use the smart button (form) or the badge (list)
to open the configuration wizard:

* Enable bank reconciliation to create/reuse **Outstanding Receipts
  (journal account)** and **Outstanding Payments (journal account)** and
  assign them to payment methods.
* Disable bank reconciliation to set all payment methods to the journal
  account.
