Marks a Point of Sale configuration as a **Seller Register**.

When enabled:

* Cash control is forced off for that POS (no opening/closing cash counting).
* New sessions open automatically and skip the opening control popup.
* Closing the register is disabled (UI and backend).
* Configuration settings can be changed while the seller session is open
  (including flexible pricelists / available pricelists).
* Payment methods used only by the seller POS can be edited without closing
  that session.

When a **cashier** POS closes its session:

* Draft orders with lines are moved to an open Seller Register session instead
  of being cancelled.
* Empty draft carts are cancelled so they do not block closing.
* If no Seller Register session is open, closing is blocked with a clear
  message (orders are not cancelled).
