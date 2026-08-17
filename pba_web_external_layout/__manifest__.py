# Part of Odoo. See LICENSE file for full copyright and licensing details.

{

    "name": "PBA Web External Layout",

    "summary": "Estilo PBA para los documentos de Odoo",

    "website": "https://github.com/OCA/l10n-venezuela",

    "author": "andyengit, Odoo Community Association (OCA)",

    "maintainers": ["andyengit"],

    "category": "Reporting",

    "version": "18.0.1.0.32",

    "depends": ["web", "sale", "account", "stock"],

    "data": [
        "report/external_layout_presupuesto.xml",
        "report/report_document_informations.xml",
        "data/report_layout_data.xml",
    ],

    "license": "AGPL-3",

    "installable": True,

}

