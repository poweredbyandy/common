1. Go to **Accounting → Accounting → Internal Transfers** and create a
   document.
2. Choose **Internal Transfer** to move an amount between two journals that
   share a currency. Set the source journal, its outgoing payment method
   and memo, the destination journal, its incoming payment method and memo,
   the date and the amount. The document memo is used on a payment that has
   no memo of its own.
3. Choose **Currency Exchange** when the journals use different currencies.
   Enter the amount that leaves and the custom rate (1 unit of the source
   currency = N units of the destination currency). You can also type the
   destination amount: the rate is recalculated.
4. The company-currency valuation shows the source at the company rate, the
   destination at your rate, and the difference. A positive difference is a
   gain.
5. Confirm. Odoo creates the outgoing payment, the incoming payment and, when
   the company-currency amounts differ, the exchange entry. The liquidity
   transfer account is reconciled.
6. Cancel from the transfer if you need to undo it. Reset to draft removes
   the canceled payments so the document can be confirmed again.
