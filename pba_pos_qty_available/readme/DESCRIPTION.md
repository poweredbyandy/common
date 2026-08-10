Show the free-to-use quantity (`free_qty`) of storable products on Point of
Sale product cards.

Quantities are scoped to the warehouse of the POS terminal, cached when the
session loads so cashiers can keep working offline, and refreshed from the
server when the connection is available again.

When the option is enabled, cashiers cannot add a storable product with no
available quantity, and cannot increase a line above the remaining free
quantity. Units already in the cart can still be paid and invoiced (selling
the last unit is allowed).

Large catalogs without product variants are loaded without performing
unnecessary archived-combination queries for every product template.
