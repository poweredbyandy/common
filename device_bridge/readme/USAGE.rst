1. Install the module.
2. Go to *Settings > Device Bridge > Devices* and click **Register device**.
3. Choose the USB device in the browser popup, set the device type
   (printer, scanner, etc.), protocol and technical code, then save.
   On a printer, click **Print test** to send a short ZPL, EPL or ESC/POS
   sample according to the device protocol.
4. Open a printer and, in the **Reports** tab, add the reports that should
   use that printer. You can also set **Device Bridge printers** on the
   report form (*Settings > Technical > Reporting > Reports*).
5. Print those reports from Odoo as usual. If the report has a Device Bridge
   printer, the job is sent to that device instead of downloading. Reports
   without a printer keep the standard Odoo download or preview.
6. From a client (POS, inventory, etc.), connect with ``DeviceBridgeProxy``
   using that device code.
7. While connected, the browser registers as an online **gateway** (heartbeat).
8. Printing uses the configured printer first (local USB already granted in
   this browser). If that USB is not on this PC, the job goes to an online
   gateway on the PC that has the printer. The USB picker opens only when
   neither the configured printer nor a gateway is available. A one-off USB
   that is not the configured printer is not saved as the default.
9. Review authorizations and gateways under *Device Bridge*.
