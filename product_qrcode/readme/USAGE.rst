#. Open a product variant or a single-variant product template.
#. Review the Product QR field. The image is drawn in the browser.
#. Print or display the image so a camera can scan it.
#. The scanner reads the barcode first, then the internal reference, then the
   product identifier.
#. To print a PDF label, open **Print Labels**, choose a sheet format
   (2 x 7, 4 x 7, 4 x 12 or Dymo) and confirm. The PDF keeps the barcode and
   adds the product QR next to it. With Product QR Code Portal installed,
   that QR encodes the portal URL.
#. To print a ZPL label, open **Print Labels** from the product form, choose
   **ZPL QR (product code)**, set the quantity and confirm. The report returns
   ZPL text ready for a thermal printer. Each label includes ``^PW`` and
   ``^LL`` from the company size, so the printer does not need ZebraSetup for
   the paper size. The field positions scale to that size so a 57 x 32 mm
   label does not overflow onto the next sticker.
#. The label prints the company QR label logo when it is set. Otherwise it
   prints the company logo.
