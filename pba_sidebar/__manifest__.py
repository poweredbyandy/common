{
    "name": "PBA Sidebar",
    "version": "18.0.1.0.0",
    "category": "Web",
    "summary": "Sidebar izquierdo de escritorio con aplicaciones e historial de navegación",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": ["web"],
    "assets": {
        "web.assets_backend": [
            "pba_sidebar/static/src/sidebar/pba_sidebar_service.js",
            "pba_sidebar/static/src/sidebar/pba_sidebar.js",
            "pba_sidebar/static/src/sidebar/pba_sidebar.xml",
            "pba_sidebar/static/src/sidebar/pba_sidebar.scss",
            "pba_sidebar/static/src/systray/sidebar_systray.js",
            "pba_sidebar/static/src/systray/sidebar_systray.xml",
        ],
    },
    "installable": True,
    "application": False,
}
