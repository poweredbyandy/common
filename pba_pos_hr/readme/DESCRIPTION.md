Restricts Point of Sale behavior when `pos_hr` employee login is enabled.

* Employees with **basic** access do not see the Pay / Payment button and
  cannot open the Payments screen. They also cannot use the Payment / Paid
  filters in the order list.
* Employees with **basic** access cannot enter the POS while the session is
  still in opening control: login is rejected and they stay on the login
  screen. Only a manager can open the register first.
* Employees with **advanced** (manager) access land on the Orders list
  (TicketScreen) after login. If the session still needs opening, the opening
  control popup is shown there. When the manager confirms the opening, the POS
  returns to the login screen so a basic cashier can enter without reloading.
