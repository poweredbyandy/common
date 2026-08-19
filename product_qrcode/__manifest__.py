{
    "name": "Product QR Code",
    "version": "18.0.1.3.1",
    "category": "Inventory/Inventory",
    "summary": "Generate and display a QR code for each product",
    "author": "andyengit",
    "maintainer": "andyengit",
    "website": "https://github.com/andyengit",
    "license": "LGPL-3",
    "depends": ["product"],
    "data": [
        "report/product_qr_paperformat.xml",
        "report/product_qr_reports.xml",
        "wizard/product_label_layout_views.xml",
        "views/product_product_views.xml",
        "views/product_template_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "product_qrcode/static/src/lib/qrcode.js",
            "product_qrcode/static/src/qr_code_field.js",
            "product_qrcode/static/src/qr_code_field.xml",
            "product_qrcode/static/src/qr_code_field.scss",
        ],
    },
    "installable": True,
    "application": False,
}
