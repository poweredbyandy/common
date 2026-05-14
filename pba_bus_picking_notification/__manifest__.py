{
    "name": "PBA Bus notificación de picking",
    "version": "18.0.1.0.0",
    "summary": "Notificación bus al crear pickings y refresco del tablero de inventario",
    "category": "Inventory/Inventory",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": ["stock", "bus"],
    "data": [
        "security/pba_bus_picking_notification_security.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "pba_bus_picking_notification/static/src/services/pba_bus_picking_notification_service.js",
            "pba_bus_picking_notification/static/src/stock_overview/pba_stock_dashboard_patch.js",
        ],
    },
    "installable": True,
    "application": False,
}
