After configuring the excluded locations, use product and inventory views as
usual.

The *Quantity On Hand* and *Free To Use Quantity* values omit quants stored in
excluded locations and their sublocations. Incoming and outgoing quantities,
reservations, transfers, and inventory adjustments keep their standard Odoo
behavior.

The product's *Update Quantity* action continues to display every physical
quant, including quants stored in excluded locations.
