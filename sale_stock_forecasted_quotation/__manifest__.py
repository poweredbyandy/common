{
    "name": "Presupuestos detallados en reporte pronosticado",
    "version": "18.0.1.0.1",
    "category": "Inventory/Inventory",
    "summary": "Muestra cada presupuesto en su propia línea del reporte pronosticado, con contacto.",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": [
        "sale_stock",
    ],
    "assets": {
        "web.assets_backend": [
            "sale_stock_forecasted_quotation/static/src/stock_forecasted/forecasted_details.xml",
        ],
    },
    "installable": True,
    "application": False,
}
