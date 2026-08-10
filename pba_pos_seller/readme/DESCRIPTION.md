Adds a **Seller** field on POS orders, separate from the **Cashier**.

* The seller is the employee who creates the order.
* The cashier can change when another employee finishes or pays the order;
  the seller stays as the original creator for traceability.
* The seller is shown in the orders list, the backend order form/list, and the
  receipt header.
* When the order is invoiced, the invoice salesperson is taken from the
  seller's linked user when available.
