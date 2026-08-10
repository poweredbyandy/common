Adds a POS setting **Ship Later by Default** (shown after Allow Ship Later).

When enabled:

* Ship Later is always active on new orders with today's date.
* On the payment screen, if the shipping date is missing it is set to today.
* Clicking the Ship Later button opens the date picker to change the delivery
  date instead of turning Ship Later off.

Also adds a **delivery address** button next to the native Invoice button
(or the invoice journal button when a localization replaces it):

* Default value is **Local** (store pickup; no delivery address required).
* The cashier can choose the customer contact or one of its delivery addresses.
* Selected addresses are used on the invoice shipping partner and stock
  deliveries.
