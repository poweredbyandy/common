1. Install the module (`pos_hr` is required).
2. In the POS configuration, assign employees to **Basic rights** or
   **Advanced rights**.
3. Before any basic cashier logs in, a manager must open the session
   (opening control). If a basic employee tries to enter earlier, login is
   rejected with an alert and the POS stays on the login screen.
4. Log in as an advanced employee while the session needs opening: the Orders
   list opens and the opening control popup is shown so the manager can open
   the register. After confirming the opening, the manager stays logged in and
   can keep working (no forced return to the employee selection screen).
5. Log in as a basic employee (after opening): the Pay button is hidden and
   the Payments screen cannot be opened; the order list hides Payment and
   Paid filters.
