Adds a **payment reference** input on bank payment lines in the POS Payment
screen.

* The value is stored on the standard field `payment_ref_no` of `pos.payment`.
* When the order is invoiced, that reference is written as the `ref` of the
  related payment journal entry (`account.move`).
* On session closing, the same reference is applied to split bank payments
  (move `ref` / payment `memo`) and included in combined bank payments when
  several references exist.
