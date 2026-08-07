{
    "name": "PBA POS UX",
    "version": "18.0.1.2.3",
    "category": "Point of Sale",
    "summary": (
        "Mejora la UX del POS: búsqueda de productos destacada con comodín *, "
        "separación categoría/producto, vista cards/lista con default_code, "
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
            "pba_pos_ux/static/src/utils/product_display_name.js",
            "pba_pos_ux/static/src/scss/pos_ux.scss",
            "pba_pos_ux/static/src/xml/navbar.xml",
            "pba_pos_ux/static/src/xml/product_screen.xml",
            "pba_pos_ux/static/src/xml/product_card.xml",
            "pba_pos_ux/static/src/xml/partner_list.xml",
            "pba_pos_ux/static/src/xml/partner_line.xml",
            "pba_pos_ux/static/src/xml/select_partner_button.xml",
            "pba_pos_ux/static/src/xml/payment_screen.xml",
            "pba_pos_ux/static/src/app/screens/partner_list/partner_list.js",
            "pba_pos_ux/static/src/app/screens/product_screen/product_screen.js",
            "pba_pos_ux/static/src/app/generic_components/product_card/product_card.js",
            "pba_pos_ux/static/src/app/models/product_product.js",
            "pba_pos_ux/static/src/app/models/pos_order_line.js",
            "pba_pos_ux/static/src/app/store/pos_store.js",
            "pba_pos_ux/static/src/app/navbar/navbar.js",
            "pba_pos_ux/static/src/app/store/opening_control_popup.js",
            "pba_pos_ux/static/src/app/screens/payment_screen/payment_screen.js",
            "pba_pos_ux/static/src/app/screens/ticket_screen/invoice_button.js",
        ],
        "web.assets_unit_tests": [
            "pba_pos_ux/static/src/utils/product_display_name.js",
            "pba_pos_ux/static/tests/unit/**/*",
        ],
    },
    "installable": True,
    "application": False,
}
