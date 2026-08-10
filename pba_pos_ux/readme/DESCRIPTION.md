Improve the visual separation between the category selector and the product
grid on the Point of Sale product screen, so cashiers can tell both areas apart
more easily. Shows clear section titles for categories and products.

Highlights the product search bar (hides the Odoo logo that was overlapping it)
and supports wildcard search with `*`. Example: `BOMB*FRE` matches
`BOMBA DE AGUA PARA FRENOS`. Search covers product name, internal reference
and barcode. Brand and internal code are added by companion bridge modules.
Products loaded from the server after the initial catalog limit use the same
POS currency conversion as products loaded when the session starts.

Allows switching the product catalog display between cards (default) and list,
both on desktop and mobile. The preference is kept in the browser. Catalog cards,
list rows and order lines show the product internal reference as
`[default_code] Product name` when available.

Does not force an active order when opening the POS. Basic and advanced
cashiers land on the orders list (TicketScreen) after login/unlock and start
work from there (open an existing draft or create one with ``+``). This avoids
two devices creating empty twin orders with the same tracking number on login.
Products can be added without a customer. A customer is required when
saving/leaving a non-empty draft (save for later, lock screen, new order, or
switch order) and when paying (orders are always invoiced).

Every order is always invoiced (the Invoice toggle is hidden on the payment
screen) and the generated invoice PDF is not downloaded automatically.

The customer button on the product and payment screens uses a full line (other
buttons wrap to the next row) and shows the partner name together with the
RIF/CI/VAT when available. The customer list also shows the RIF/CI/VAT under
each partner name and a pencil button to edit the customer directly.

Adds a **Pedidos** button next to the order tabs ``+`` in the POS header to open
the orders list (TicketScreen) in one click. The POS navbar is compacted
(shorter bar, smaller controls and search) to keep the header lighter.

Persists open orders when creating a new one or locking the POS, and adds a
renewable multi-device lock (30 seconds, heartbeat every 10 seconds) so only one
device can edit a shared draft order at a time. Devices refresh who is inside
each order before opening and while the orders list is open. Occupied orders
hide the delete button. Already processed orders (non-draft) cannot be opened.
Shows a loading blocker when closing the POS / register so the UI does not look
idle while closing data is prepared or the session is closed.
After payment, the lock is released and the receipt returns to the orders list;
tiny payment rounding gaps are auto-aligned before validation. Draft orders
(including total 0) are selected in the list with one click and opened with
**Load Order**. Leaving an order with no products deletes it. Offline, new local orders remain allowed, shared orders
cannot be opened, and the pending sync count is shown in the connection
indicator.
