This module stores a QR value for every product variant. The encoded value is
the product barcode, the internal reference when no barcode is set, or the
product identifier as a last resort.

The product form draws the QR image in the browser from that value, so opening
a product does not generate images on the server.

Standard PDF product labels (2x7, 4x7, 4x12 and Dymo) print that QR next to
the barcode.

ZPL labels can print a company-specific QR label logo. If that logo is empty,
the company logo is used.

The ZPL print width and label length are taken from the company label size.
The default is 57 x 31 mm so a 57 x 32 mm gap label does not skip a blank
sticker. The size can be entered in millimeters, centimeters, inches or
printer dots.
