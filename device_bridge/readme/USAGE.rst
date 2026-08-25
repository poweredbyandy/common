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
8. On the PC that has the printer, Odoo keeps a gateway online. From another
   device, print jobs are queued and the printer PC pulls them to print. If
   the gateway is not found, Odoo asks whether to print on this computer.
9. Review authorizations and gateways under *Device Bridge*.
10. Open *Device Bridge > Print queue* to see pending jobs. Select stuck
    jobs and delete them so they are not printed later.
