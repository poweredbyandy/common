After configuring the excluded locations, use product and inventory views as
usual.

The *Quantity On Hand* value includes every physical quant. The *Free To Use
Quantity* value omits the unreserved stock stored in excluded locations and
their sublocations.

In the product's *Update Quantity* action, excluded quants remain visible with
their physical *On Hand* value while their *Available* value is zero.

The *Available Products* filter only returns products with a positive free
quantity after applying the location exclusions.

Forecasted, incoming, and outgoing quantities, reservations, transfers, and
inventory adjustments keep their standard Odoo behavior.
