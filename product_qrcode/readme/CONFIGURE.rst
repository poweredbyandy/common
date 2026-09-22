#. Go to **Settings > Users & Companies > Companies** and open the company.
#. In **General Information**, use the **Product QR Label** group.
#. Upload **QR Label Logo** to print that image on ZPL QR labels.
#. If the field is empty, the label uses the company logo. The default Odoo
   logo is not printed.
#. The default size is **57 x 31 mm** at 203 dpi, for 57 x 32 mm gap labels.
   The extra millimeter is left for the gap sensor.
#. To use another roll, set the unit and the physical width and height. Do
   not include the gap between labels.
#. Click **Calibrate Zebra media**. The printer feeds a few labels, measures
   the gap (same idea as ZebraSetup) and stores that length. After that,
   print jobs omit ``^LL`` and follow the printer.
