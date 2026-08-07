{
    "name": "Mail WhatsApp Sale",
    "version": "18.0.1.2.1",
    "category": "Sales/Sales",
    "summary": "WhatsApp templates to send quotations, sale orders and invoices with portal link button",
    "author": "andyengit",
    "maintainer": "andyengit",
    "website": "https://github.com/andyengit",
    "license": "LGPL-3",
    "depends": ["mail_whatsapp", "sale"],
    "data": [
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
