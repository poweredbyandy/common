{
    "name": "PBA Finnancial Risk",
    "version": "18.0.1.0.5",
    "summary": "Acceso rapido al riesgo financiero desde ventas y facturas",
    "category": "Accounting",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": [
        "sale_management",
        "account",
        "account_financial_risk",
        "sale_financial_risk",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/res_partner_views.xml",
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
        "views/res_company_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "pba_finnancial_risk/static/src/js/risk_dashboard_field.js",
            "pba_finnancial_risk/static/src/xml/risk_dashboard_field.xml",
            "pba_finnancial_risk/static/src/scss/risk_dashboard.scss",
        ],
    },
    "installable": True,
    "application": False,
}
