==============================
Sale Stock Availability Color
==============================

Description
===========

This module changes the sales order stock availability icon colors:

* Green when there is on-hand inventory for the ordered quantity.
* Orange when there is no on-hand inventory but the forecast covers the quantity.
* Red when there is neither on-hand inventory nor a covering forecast.

Use Cases / Context
===================

Odoo marks the sales availability icon as available when the forecast is enough,
even if the warehouse has no on-hand quantity. Users need to distinguish stock
already in inventory from incoming or planned replenishment.

Usage
=====

#. Open a quotation or sales order with storable products.
#. Check the availability chart icon on each order line.
#. Green means the quantity is already in inventory.
#. Orange means the quantity is not in inventory but is forecasted.
#. Red means the quantity is not in inventory and has no covering forecast.
#. Click the icon to open the standard availability popover and forecast.

Authors
=======

* andyengit

Contributors
============

* andyengit
