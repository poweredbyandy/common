This module stores a QR value for every product variant. The encoded value is
the product barcode, the internal reference when no barcode is set, or the
product identifier as a last resort.

The product form draws the QR image in the browser from that value, so opening
a product does not generate images on the server.
