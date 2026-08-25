Authorize and share hardware devices across browsers and computers.

* Define devices (code, protocol, USB filters, allowed connection types).
* Authorize a physical device per Odoo user and browser (``browser_key``).
* Local transport today: **WebUSB** (more transports can be added later).
* **WebSocket gateway**: while a browser keeps the physical device connected,
  other users/devices in the same company can send jobs to it through Odoo bus.
* Frontend proxy tries local connection first, then falls back to a remote
  online gateway.
* Assign ``ir.actions.report`` records to a printer so each device has a
  configured report list. Printing those reports sends the job to the
  device; other reports keep the standard Odoo behavior.
