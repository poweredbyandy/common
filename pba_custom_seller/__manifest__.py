{
    "name": "PBA Custom Seller",
    "version": "18.0.1.4.0",
    "category": "Sales",
    "summary": "Limited seller: own contacts, SO contacts, pricelist products, optional qty/confirm",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": [
        "sale_stock",
        "product_pricelist_group",
    ],
    "data": [
        "security/pba_custom_seller_security.xml",
        "views/product_views.xml",
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "application": False,
}
