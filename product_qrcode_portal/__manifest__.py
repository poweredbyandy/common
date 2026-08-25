{
    "name": "Product QR Code Portal",
    "version": "18.0.1.3.1",
    "category": "Website/Website",
    "summary": "Configure what happens when a product portal QR is scanned",
    "author": "andyengit",
    "maintainer": "andyengit",
    "website": "https://github.com/andyengit",
    "license": "LGPL-3",
    "depends": [
        "website_sale",
        "product_qrcode",
    ],
    "data": [
        "views/product_qr_portal_templates.xml",
        "views/res_config_settings_views.xml",
        "views/website_views.xml",
        "views/product_product_views.xml",
        "views/product_template_views.xml",
    ],
    "installable": True,
    "application": False,
}
