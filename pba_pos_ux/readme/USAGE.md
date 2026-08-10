1. Install the module.
2. Open a Point of Sale session.
3. On the product screen, the sections are labeled (Categorías / Productos) and
   appear with a larger gap and a subtle divider. The product search bar is
   wider and the Odoo logo is hidden so it does not overlap the search.
4. Search products by name, reference or barcode. Use `*` as a wildcard between
   fragments, e.g. `BOMB*FRE` for `BOMBA DE AGUA PARA FRENOS`. Press **Enter**
   in the search box (or click **Search more**) to query the server with the
   same pattern. Products found on the server are shown using the configured
   POS currency.
5. Switch the catalog between cards and list with the toggle next to Productos.
   Products with an internal reference (`default_code`) appear as
   `[CODE] Product name` in the catalog (cards/list) and in the order lines.
   In list mode, the product row highlight exists only while the search box has
   focus (and there is a search term). Use Up/Down to move in the list.
   Backspace/Delete clears the search; pressed again (empty search) focuses the
   order lines and clears the product row highlight.
5b. On desktop, the numeric keypad is hidden by default. Use **Mostrar teclado**
    / **Ocultar teclado** under the order controls to show or hide it. The
    choice is remembered in the browser. On mobile the keypad is unchanged.
6. After updating the module, reopen the POS session and hard-refresh the
   browser (or regenerate assets) so the new scripts load.
7. After login/unlock (basic or advanced cashier), the POS opens the orders
   list. There is no active order until you open one or press ``+``. Opening
   **Pedidos** leaves the current order (saves it, releases the lock and clears
   the active order). Adding products does not force a customer. A customer is
   required when saving/leaving a non-empty draft (save, lock, Pedidos, new
   order, or switch order) and when paying. Saving for later returns to the
   orders list.
8. On payment, orders are always invoiced (no Invoice toggle). The invoice PDF
   is not downloaded. No extra configuration is required.
9. The customer button shows the full name and RIF/CI/VAT on its own row; other
   action buttons appear on the following row.
10. In the customer list, each partner shows its RIF/CI/VAT under the name and
    a pencil button to open the customer form for editing. Search is partial
    (e.g. `Negrete` finds `Comercializadora el Negrete`) and also supports the
    same `*` wildcard as products (e.g. `MAR*LOP`). Press **Enter** or
    **Search more** to query the server with that pattern.
11. Next to the ``+`` of floating orders in the header, use **Pedidos** to open
    the orders list.
12. Multi-device order locking:
    - Creating a new order (``+``) or locking the POS saves the current draft
      order and releases its lock so other devices can take it.
    - Opening a shared draft order acquires a 30-second lock for this device.
      The lock is renewed every 10 seconds while the order stays open.
    - Before opening, and while **Pedidos** is open, devices refresh who is
      inside each order from the server (avatar + tooltip).
    - Only the device holding the lock can edit that order. Others cannot open
      it and do not see the delete (trash) button while someone is inside.
    - Orders already processed (paid/done/cancelled, not draft) cannot be opened
      again; the POS shows an alert and stays on the orders list.
    - After a successful payment, the lock is released and leaving the receipt
      returns to the orders list. If the server rejects the payment (for example
      a 0.01 rounding gap), the POS stays on Payment and shows an alert.
    - Click a draft order in the list (including total 0) to select it, then
      use **Load Order** to open it.
    - Leaving an order with no products deletes it automatically.
    - Floating order tabs on the left show only the order currently open on
      this device.
    - Offline: you can still create local orders. Shared/server orders cannot
      be opened until the connection is back. Pending orders to sync appear as
      a counter next to the connection status.

For brand or internal-code search, install the companion modules
`pba_pos_ux_product_brand` and/or `pba_pos_ux_internal_code` (auto-installed
when their dependencies are present).

Concurrency benchmark
---------------------

Run the isolated multi-cursor benchmark on a disposable test database:

```
odoo-bin -d <test_database> -u pba_pos_ux --stop-after-init \
    --test-enable --test-tags=pba_lock_benchmark
```

The benchmark creates 120 draft orders in one POS session and uses 8 concurrent
workers sharing the same Odoo user but reporting different employees and device
tokens. It verifies simultaneous acquisition, rejected intrusions, release,
owner stability, session stability, and that no order disappears. A separate
8-worker race verifies that exactly one terminal obtains the same order.
Throughput for each phase is written to the Odoo test log.
