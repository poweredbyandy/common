{
    "name": "PBA Provider Subscription",
    "version": "18.0.1.5.1",
    "category": "Services/Helpdesk",
    "summary": "Tickets de soporte y resumen financiero para clientes conectados por RPC",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": [
        "mail",
        "portal",
        "account",
    ],
    "data": [
        "security/pba_provider_subscription_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/ir_config_parameter_data.xml",
        "wizard/pba_subscription_api_key_wizard_views.xml",
        "views/pba_support_ticket_views.xml",
        "views/res_partner_views.xml",
        "views/pba_support_ticket_menus.xml",
    ],

    "installable": True,
    "application": True,
}
