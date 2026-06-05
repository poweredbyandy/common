ACCOUNT_TEMPLATES = {
    "whatsapp_template_overdue": {
        "name": "PBA Cuenta por cobrar vencida",
        "header": "Recordatorio de pago",
        "body": (
            "Estimado/a {{1}}, le recordamos que la factura {{2}} por {{3}} "
            "se encuentra vencida desde {{4}}. "
            "Puede revisar el pedido con el botón inferior."
        ),
        "footer": "Departamento de cobranzas",
        "category": "utility",
        "language": "es",
        "state": "draft",
        "model": "account.move",
        "variables": [
            {"position": 1, "field": "partner_id"},
            {"position": 2, "field": "name"},
            {"position": 3, "field": "amount_residual"},
            {"position": 4, "field": "invoice_date_due"},
            {"position": 5, "source_type": "sale_order_portal_url"},
        ],
        "buttons": [
            {
                "sequence": 10,
                "name": "Ver pedido",
                "button_type": "url",
                "url_source": "portal_preview",
                "variable_position": 5,
            }
        ],
    },
}

ACCOUNT_COMPANY_FIELDS = {
    "whatsapp_template_overdue_id": "whatsapp_template_overdue",
}
