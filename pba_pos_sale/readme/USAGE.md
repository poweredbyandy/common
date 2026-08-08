1. Install the module (`point_of_sale` and `sale` are required).
2. Open a Point of Sale session.
3. Select a customer and add products to the order.
4. Open **Actions** and click **Generar Presupuesto**.
5. Confirm the dialog. A draft quotation is created in Sales and the POS
   order is removed.
6. Open Sales → Quotations to review or send the new quotation.
7. To settle an existing quotation from POS, click **Cotizaciones/Orden** next
   to **Pedidos** in the navbar (or **Quotation/Order** in Actions). Orders in
   the POS currency or in any loaded pricelist currency are shown. If a
   customer is selected on the current order, only that customer's orders
   appear. The quotation is settled directly (no down-payment prompt) and
   foreign-currency amounts are converted to the POS currency (e.g. USD → VES).
