SALE_TEMPLATES = {
    "whatsapp_template_sale_quotation": {
        "name": "PBA Presupuesto",
        "header": "Presupuesto",
        "body": (
            "Hola {{1}}, le enviamos su presupuesto {{2}} por un monto de {{3}}. "
            "Puede revisarlo con el botón inferior."
        ),
        "footer": "Gracias por su preferencia",
        "category": "utility",
        "language": "es",
        "state": "draft",
        "model": "sale.order",
        "record_states": "draft,sent",
        "variables": [
            {"position": 1, "field": "partner_id"},
            {"position": 2, "field": "name"},
            {"position": 3, "field": "amount_total"},
            {"position": 4, "source_type": "portal_url"},
        ],
        "buttons": [
            {
                "sequence": 10,
                "name": "Ver presupuesto",
                "button_type": "url",
                "url_source": "portal_preview",
                "variable_position": 4,
            }
        ],
    },
    "whatsapp_template_sale_confirmed": {
        "name": "PBA Pedido confirmado",
        "header": "Pedido confirmado",
        "body": (
            "Hola {{1}}, su pedido {{2}} ha sido confirmado por un total de {{3}}. "
            "Puede revisarlo con el botón inferior."
        ),
        "footer": "Gracias por su compra",
        "category": "utility",
        "language": "es",
        "state": "draft",
        "model": "sale.order",
        "record_states": "sale",
        "variables": [
            {"position": 1, "field": "partner_id"},
            {"position": 2, "field": "name"},
            {"position": 3, "field": "amount_total"},
            {"position": 4, "source_type": "portal_url"},
        ],
        "buttons": [
            {
                "sequence": 10,
                "name": "Ver pedido",
                "button_type": "url",
                "url_source": "portal_preview",
                "variable_position": 4,
            }
        ],
    },
    "whatsapp_template_delivery_done": {
        "name": "PBA Entrega realizada",
        "header": "Entrega",
        "body": (
            "Hola {{1}}, su entrega del pedido {{2}} ha sido realizada. "
            "Puede revisar el seguimiento del pedido con el botón inferior."
        ),
        "footer": "Gracias",
        "category": "utility",
        "language": "es",
        "state": "draft",
        "model": "stock.picking",
        "record_states": "done",
        "variables": [
            {"position": 1, "field": "partner_id"},
            {"position": 2, "field": "sale_id"},
            {"position": 3, "source_type": "sale_order_portal_url"},
        ],
        "buttons": [
            {
                "sequence": 10,
                "name": "Ver pedido",
                "button_type": "url",
                "url_source": "portal_preview",
                "variable_position": 3,
            }
        ],
    },
}

SALE_COMPANY_FIELDS = {
    "whatsapp_template_sale_quotation_id": "whatsapp_template_sale_quotation",
    "whatsapp_template_sale_confirmed_id": "whatsapp_template_sale_confirmed",
    "whatsapp_template_delivery_done_id": "whatsapp_template_delivery_done",
}
