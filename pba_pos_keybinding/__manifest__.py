{
    "name": "PBA POS Keybinding",
    "version": "18.0.1.0.0",
    "category": "Point of Sale",
    "summary": (
        "Atajos del POS con Shift: muestra letras sobre los botones "
        "para acceder rapido (buscar, pedidos, cliente, pagar, etc.)."
    ),
    "author": "andyengit",
    "maintainer": "andyengit",
    "website": "https://github.com/andyengit",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
        "pba_pos_ux",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pba_pos_keybinding/static/src/scss/keybinding.scss",
            "pba_pos_keybinding/static/src/app/keybinding.js",
            "pba_pos_keybinding/static/src/xml/keybinding.xml",
        ],
    },
    "installable": True,
    "application": False,
}
