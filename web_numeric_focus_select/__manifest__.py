{
    "name": "Seleccionar números al enfocar",
    "version": "18.0.1.0.0",
    "category": "Hidden",
    "summary": "Selecciona todo el valor al enfocar campos enteros o decimales.",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": [
        "web",
    ],
    "data": [
        "views/res_users_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "web_numeric_focus_select/static/src/js/numeric_focus_select.esm.js",
        ],
    },
    "installable": True,
    "application": False,
}
