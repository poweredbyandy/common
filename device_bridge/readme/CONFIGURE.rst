* Grant *Device Bridge / Manager* to users who maintain the device catalog.
* Internal users can authorize their own devices and see their gateways.
* Ensure ``websocket`` is listed in the device ``connection_types`` field if
  remote sharing is required (default includes ``webusb,websocket``).
* Clients must use a Chromium browser over HTTPS (or localhost) for WebUSB.
* On a printer or label printer, open the **Reports** tab and select the
  ``ir.actions.report`` records that this device should print.
* The same assignment is available on each report form as
  **Device Bridge printers**.
