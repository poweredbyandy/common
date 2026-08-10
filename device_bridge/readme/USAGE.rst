1. Install the module.
2. Go to *Settings > Device Bridge > Devices* and click **Register device**.
3. Choose the USB device in the browser popup, set the device type
   (printer, scanner, etc.), protocol and technical code, then save.
4. From a client (POS, inventory, etc.), connect with ``DeviceBridgeProxy``
   using that device code.
5. While connected, the browser registers as an online **gateway** (heartbeat).
6. Another device without USB can print with ``printRaw(..., { mode: 'auto' })``:
   it uses local USB when available, otherwise sends the job to an online
   gateway.
7. Review authorizations and gateways under *Device Bridge*.
