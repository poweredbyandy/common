{
    "name": "Sincronización de propiedades de contacto entre compañías",
    "version": "18.0.1.0.0",
    "category": "Sales/CRM",
    "summary": "Sincroniza lista de precios, términos de pago y límite de crédito entre compañías.",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": [
        "account",
        "contacts",
        "product",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/partner_company_property_sync_wizard_views.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": False,
}
