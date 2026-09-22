This module adds a portal QR next to the product QR. The portal QR always
encodes /product-qr?code=VALUE, so the printed code stays valid when the
scan action changes. The image is drawn in the browser from that URL.

PDF product labels use that portal URL in the QR when this module is
installed. The linear barcode still prints the product barcode.

The website can be configured to:

* read only the product code
* open the eCommerce product page
* open the Scan and Order portal

Helpers extract the product code from a raw value, a portal URL, or an
/auto-order URL.
