{
    "name": "PBA Image Expand",
    "version": "18.0.1.0.0",
    "summary": "Expandir imagenes del widget image a pantalla completa",
    "category": "Web",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": ["web"],
    "assets": {
        "web.assets_backend": [
            "pba_image_expand/static/src/js/image_field_expand_patch.js",
            "pba_image_expand/static/src/xml/image_field_expand.xml",
            "pba_image_expand/static/src/scss/image_field_expand.scss",
        ],
    },
    "installable": True,
    "application": False,
}
