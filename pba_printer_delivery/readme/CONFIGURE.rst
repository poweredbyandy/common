#. Install **Device Bridge** on the database that has the POS-80 (recommended).
#. Upgrade Device Bridge so the print-job table exists.
#. Open the report **POS-80 Delivery Ticket** (or the Device Bridge printer)
   and select the printer(s) in **Device Bridge printers** / **Reports**.
#. The module links the ``pos80`` printer to this report when Device Bridge is
   present.
#. Keep a Chrome or Edge tab connected so the gateway stays online, or print
   from the computer that has the USB cable.
#. Grant **Receive picking notifications** to warehouse users so their browsers
   can print locally when no gateway is online.
#. Inventory settings: enable or disable **Auto-print POS-80** per company.
