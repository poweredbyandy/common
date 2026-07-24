{
    "name": "PBA POS UX",
    "version": "18.0.1.0.4",
    "category": "Point of Sale",
    "summary": (
        "Mejora la UX del POS: separación categoría/producto, "
        "cliente obligatorio y facturación siempre sin descarga de PDF."
    ),
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pba_pos_ux/static/src/scss/pos_ux.scss",
            "pba_pos_ux/static/src/xml/product_screen.xml",
            "pba_pos_ux/static/src/xml/partner_list.xml",
            "pba_pos_ux/static/src/xml/partner_line.xml",
            "pba_pos_ux/static/src/xml/select_partner_button.xml",
            "pba_pos_ux/static/src/xml/payment_screen.xml",
            "pba_pos_ux/static/src/app/screens/partner_list/partner_list.js",
            "pba_pos_ux/static/src/app/store/pos_store.js",
            "pba_pos_ux/static/src/app/store/opening_control_popup.js",
            "pba_pos_ux/static/src/app/screens/payment_screen/payment_screen.js",
            "pba_pos_ux/static/src/app/screens/ticket_screen/invoice_button.js",
        ],
    },
    "installable": True,
    "application": False,
}
