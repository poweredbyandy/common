1. Install the module.
2. Open a Point of Sale session.
3. On the product screen, the sections are labeled (Categorías / Productos) and
   appear with a larger gap and a subtle divider. The product search bar is
   wider and the Odoo logo is hidden so it does not overlap the search.
4. Search products by name, reference or barcode. Use `*` as a wildcard between
   fragments, e.g. `BOMB*FRE` for `BOMBA DE AGUA PARA FRENOS`. Press Enter /
   Search more to also query the server with the same pattern.
5. Switch the catalog between cards and list with the toggle next to Productos.
   Products with an internal reference (`default_code`) appear as
   `[CODE] Product name` in the catalog (cards/list) and in the order lines.
   After updating the module, reopen the POS session and hard-refresh the
   browser (or regenerate assets) so the new scripts load.
6. When you create a new order, the customer list opens automatically and stays
   mandatory until you select or create a contact (Discard/close are blocked).
   Adding products or paying is not possible without a customer.
7. On payment, orders are always invoiced (no Invoice toggle). The invoice PDF
   is not downloaded. No extra configuration is required.
8. The customer button shows the full name and RIF/CI/VAT on its own row; other
   action buttons appear on the following row.
9. In the customer list, each partner shows its RIF/CI/VAT under the name.

For brand or internal-code search, install the companion modules
`pba_pos_ux_product_brand` and/or `pba_pos_ux_internal_code` (auto-installed
when their dependencies are present).
