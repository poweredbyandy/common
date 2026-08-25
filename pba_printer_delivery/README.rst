===========================
PBA POS-80 Delivery Printer
===========================

Print outgoing pickings on an 80 mm ESC/POS thermal printer (POS-80).

Description
===========

* Builds a delivery ticket with customer, origin, date and product lines
  grouped by source location (quantity and code, then the product name).
* Prints automatically when an outgoing picking is created.
* Adds a **Print POS-80** button and the **POS-80 Delivery Ticket** report.
  Assign Device Bridge printers on that report.
* Uses Device Bridge for the USB or gateway connection when that module is
  installed. This module does not depend on Device Bridge.

Use Cases / Context
===================

Warehouse staff need the delivery ticket as soon as a picking exists, without
opening a report dialog. The ticket must reach the POS-80 that is already
shared through Device Bridge, including a browser that keeps the printer online
as a gateway.

Configuration
=============

#. Install **Device Bridge** on the database that has the POS-80 (recommended).
#. Create the printer in Device Bridge (name, code, USB filters) yourself.
#. Open the report **POS-80 Delivery Ticket** (or the Device Bridge printer)
   and assign that printer in **Device Bridge printers** / **Reports**.
#. Keep a Chrome or Edge tab connected so the gateway stays online, or print
   from the computer that has the USB cable.
#. Grant **Receive picking notifications** to warehouse users so their browsers
   can print locally when no gateway is online.
#. Inventory settings: enable or disable **Auto-print POS-80** per company.

Usage
=====

#. Confirm a sales order or create an outgoing picking. The POS-80 prints the
   delivery ticket when auto-print is enabled. Lines are grouped by source
   location.
#. Open the picking and click **Print POS-80**, or use **Print > POS-80
   Delivery Ticket**.
#. If the configured printer is offline, the client asks whether to print on
   this computer and opens the USB picker.

Authors
=======

* andyengit

Contributors
============

* andyengit
