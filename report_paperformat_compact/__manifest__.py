{
    "name": "Report Paperformat Compact",
    "summary": "US Letter compacto y encabezado de una sola franja",
    "version": "18.0.1.2.0",
    "category": "Reporting",
    "author": "andyengit",
    "maintainers": ["andyengit"],
    "website": "https://github.com/andyengit",
    "license": "LGPL-3",
    "depends": ["web", "stock", "stock_picking_batch"],
    "data": [
        "data/report_paperformat.xml",
        "data/report_paperformat_assignment.xml",
        "report/external_layout_letter_compact.xml",
        "report/report_delivery_slip.xml",
        "data/report_layout_data.xml",
    ],
    "assets": {
        "web.report_assets_common": [
            "report_paperformat_compact/static/src/scss/delivery_slip_compact.scss",
        ],
    },
    "installable": True,
    "application": False,
}
