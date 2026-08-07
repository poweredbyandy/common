Improve the visual separation between the category selector and the product
grid on the Point of Sale product screen, so cashiers can tell both areas apart
more easily. Shows clear section titles for categories and products.

Highlights the product search bar (hides the Odoo logo that was overlapping it)
and supports wildcard search with `*`. Example: `BOMB*FRE` matches
`BOMBA DE AGUA PARA FRENOS`. Search covers product name, internal reference
and barcode. Brand and internal code are added by companion bridge modules.

Allows switching the product catalog display between cards (default) and list,
both on desktop and mobile. The preference is kept in the browser. Catalog cards,
list rows and order lines show the product internal reference as
`[default_code] Product name` when available.

Also requires a customer on every order: when a new order is created the customer
list opens automatically so the cashier can select or create a contact, without
showing an alert dialog.

Every order is always invoiced (the Invoice toggle is hidden on the payment
screen) and the generated invoice PDF is not downloaded automatically.

The customer button on the product and payment screens uses a full line (other
buttons wrap to the next row) and shows the partner name together with the
RIF/CI/VAT when available. The customer list also shows the RIF/CI/VAT under
each partner name.
