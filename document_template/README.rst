==================
Document Templates
==================

Create reusable document templates linked to any Odoo model. Write the
page with the HTML editor, insert fields from the record, and print a PDF
already filled with that record's data from the Print menu.

**Table of contents**

.. contents::
   :local:

Use Cases / Context
===================

Teams often need letters, certificates or agreements that look like a
Word document but must always pull live data from Odoo (partner name,
amounts, dates). Maintaining a separate file outside Odoo leads to stale
copies. This module keeps the template and the print action inside Odoo.

Configuration
=============

1. Install **Document Templates**.
2. Ensure ``wkhtmltopdf`` is available on the server (same requirement as
   every Odoo PDF report).
3. Open **Document Templates** and create a template for the target
   model.
4. Optionally set a paper format and whether to wrap the page with the
   company external layout.
5. Use **Add to Print menu** so users can print from records of that
   model.

Usage
=====

1. Open **Document Templates** and create a template.
2. Choose the model (for example Contact or Sales Order).
3. Write the body. Use the dynamic field picker (``/`` or the field button)
   to insert values such as the partner name.
4. Click **Preview** to render the template against a sample record.
5. Click **Add to Print menu**.
6. Open a record of that model and use **Print** to download the filled
   PDF.

Bug Tracker
===========

Bugs are tracked on GitHub Issues. In case of trouble, please check there
if your issue has already been reported.

Credits
=======

Authors
-------

* andyengit

Contributors
------------

* andyengit <anderson.armeya@gmail.com>

Maintainers
-----------

This module is maintained by andyengit.
