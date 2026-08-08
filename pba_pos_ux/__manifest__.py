{
    "name": "PBA POS UX",
    "version": "18.0.1.5.6",
    "category": "Point of Sale",
    "summary": (
        "Mejora la UX del POS: búsqueda de productos destacada con comodín *, "
        "separación categoría/producto, vista cards/lista con default_code, "
        "navegación por teclado en lista, apertura en lista de pedidos, "
        "cliente obligatorio al guardar/salir del pedido o pagar, "
        "facturación siempre sin descarga "
        "de PDF, y persistencia/bloqueo multidispositivo de pedidos abiertos."
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
            "pba_pos_ux/static/src/utils/order_lock.js",
            "pba_pos_ux/static/src/scss/pos_ux.scss",
            "pba_pos_ux/static/src/xml/navbar.xml",
            "pba_pos_ux/static/src/xml/order_tabs.xml",
            "pba_pos_ux/static/src/xml/ticket_screen.xml",
            "pba_pos_ux/static/src/xml/product_screen.xml",
            "pba_pos_ux/static/src/xml/order_summary.xml",
            "pba_pos_ux/static/src/xml/control_buttons.xml",
            "pba_pos_ux/static/src/xml/action_pad.xml",
            "pba_pos_ux/static/src/xml/product_card.xml",
            "pba_pos_ux/static/src/xml/partner_list.xml",
            "pba_pos_ux/static/src/xml/partner_line.xml",
            "pba_pos_ux/static/src/xml/select_partner_button.xml",
            "pba_pos_ux/static/src/xml/payment_screen.xml",
            "pba_pos_ux/static/src/app/screens/partner_list/partner_list.js",
            "pba_pos_ux/static/src/app/screens/product_screen/product_screen.js",
            "pba_pos_ux/static/src/app/screens/product_screen/order_summary.js",
            "pba_pos_ux/static/src/app/screens/ticket_screen/ticket_screen.js",
            "pba_pos_ux/static/src/app/generic_components/product_card/product_card.js",
            "pba_pos_ux/static/src/app/models/product_product.js",
            "pba_pos_ux/static/src/app/models/pos_order_line.js",
            "pba_pos_ux/static/src/app/store/pos_store.js",
            "pba_pos_ux/static/src/app/navbar/navbar.js",
            "pba_pos_ux/static/src/app/components/order_tabs/order_tabs.js",
            "pba_pos_ux/static/src/app/screens/payment_screen/payment_screen.js",
            "pba_pos_ux/static/src/app/screens/receipt_screen/receipt_screen.js",
            "pba_pos_ux/static/src/app/screens/ticket_screen/invoice_button.js",
        ],
        "web.assets_unit_tests": [
            "pba_pos_ux/static/src/utils/product_display_name.js",
            "pba_pos_ux/static/src/utils/order_lock.js",
            "pba_pos_ux/static/tests/unit/**/*",
        ],
    },
    "installable": True,
    "application": False,
}
