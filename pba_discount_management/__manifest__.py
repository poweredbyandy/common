{
    "name": "PBA Discount Management",
    "version": "18.0.1.0.0",
    "summary": "Límites de descuento por compañía, contacto y permisos de descuento global",
    "category": "Sales",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": [
        "sale_management",
        "account",
    ],
    "data": [
        "security/pba_discount_management_groups.xml",
        "views/res_config_settings_views.xml",
        "views/res_partner_views.xml",
        "views/sale_order_views.xml",
        "views/pba_hide_line_discount_views.xml",
    ],
    "installable": True,
    "application": False,
}
