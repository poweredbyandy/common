{
    "name": "Informes ESC/POS (WebSerial)",
    "version": "18.0.1.2.0",
    "category": "Reporting",
    "summary": "Informes QWeb ESC/POS por WebSerial (COM) o WebUSB",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": ["web"],
    "data": [
        "data/report_escpos_templates.xml",
        "views/ir_actions_report_views.xml",
    ],
    "demo": [
        "demo/report_escpos_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "report_escpos_webserial/static/src/js/report_escpos_action.js",
        ],
    },
    "installable": True,
    "application": False,
}
