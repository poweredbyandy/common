Send a quotation by WhatsApp
============================

#. Open a quotation in **Sales** (state Draft or Quotation Sent).
#. Make sure the customer has a phone/mobile number.
#. Click **WhatsApp Cotización** in the order header.
#. The customer receives the approved template with a button to open the
   portal page of that quotation.

Send a sale order by WhatsApp
=============================

#. Open a confirmed sale order (state Sales Order).
#. Click **WhatsApp Orden** in the header.
#. The customer receives the order template with a portal link button.

Send an invoice by WhatsApp
===========================

#. Open a posted customer invoice that comes from a sales order.
#. Click **WhatsApp Factura** in the header.
#. The customer receives the invoice template with a button that opens the
   related **sale order** portal page.
#. If the invoice has no related sales order, the button is hidden and sending
   is blocked with an error.

Templates
=========

On install, the module creates (or updates) these WhatsApp templates on the
active account:

* ``sale_quotation`` – Send Quotation (model ``sale.order``)
* ``sale_order`` – Sale Order (model ``sale.order``)
* ``sale_invoice`` – Invoice (model ``account.move``, button URL → sale order)

In Demo they are auto-approved. In Test/Production, submit them to Meta from
**WhatsApp → Templates** before sending.
