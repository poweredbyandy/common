* Grant *Device Bridge / Manager* to users who maintain the device catalog.
* Internal users can authorize their own devices and see their gateways.
* Ensure ``websocket`` is listed in the device ``connection_types`` field if
  remote sharing is required (default includes ``webusb,websocket``).
* Clients must use a Chromium browser over HTTPS (or localhost) for WebUSB.
