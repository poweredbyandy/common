After configuring the excluded locations, use product and inventory views as
usual.

The *Quantity On Hand* and *Free To Use Quantity* values omit the stock stored
in excluded locations and their sublocations. Products whose remaining stock is
only in excluded locations are not returned by the *Available Products* filter.

In the product's *Update Quantity* action, excluded quants remain visible with
their physical *On Hand* value while their *Available* value is zero.

Forecasted, incoming, and outgoing quantities, reservations, transfers, and
inventory adjustments keep their standard Odoo behavior.
