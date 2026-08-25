{
    "name": "Website Auto Order Scanner",
    "version": "18.0.1.8.3",
    "category": "Website/Website",
    "summary": "Public OWL portal to scan barcodes or QR codes and buy with the website cart",
    "author": "andyengit",
    "maintainer": "andyengit",
    "website": "https://github.com/andyengit",
    "license": "LGPL-3",
    "depends": [
        "website_sale",
        "product_qrcode",
        "product_qrcode_portal",
    ],
    "data": [
        "data/website_menu.xml",
        "views/auto_order_templates.xml",
        "views/res_config_settings_views.xml",
        "views/website_views.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "web_sale_auto_order/static/src/auto_order.scss",
            "web_sale_auto_order/static/src/auto_order.js",
            "web_sale_auto_order/static/src/auto_order.xml",
        ],
        "web_sale_auto_order.zxing_assets": [
            "web/static/lib/zxing-library/zxing-library.js",
        ],
    },
    "installable": True,
    "application": False,
}
