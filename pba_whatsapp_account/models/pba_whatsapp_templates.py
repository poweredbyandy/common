ACCOUNT_TEMPLATES = {
    "whatsapp_template_invoice": {
        "name": "PBA Factura cliente",
        "header": "Factura",
        "body": "Estimado cliente, le enviamos su factura. Quedamos atentos ante cualquier consulta.",
        "footer": "Gracias",
        "category": "utility",
        "language": "es",
        "state": "draft",
    },
    "whatsapp_template_payment": {
        "name": "PBA Pago registrado",
        "header": "Pago recibido",
        "body": "Hemos registrado su pago correctamente. Gracias por su confianza.",
        "footer": "Gracias",
        "category": "utility",
        "language": "es",
        "state": "draft",
    },
    "whatsapp_template_overdue": {
        "name": "PBA Cuenta por cobrar vencida",
        "header": "Recordatorio de pago",
        "body": "Le recordamos que tiene una factura pendiente de pago. Por favor contáctenos para regularizar su cuenta.",
        "footer": "Departamento de cobranzas",
        "category": "utility",
        "language": "es",
        "state": "draft",
    },
}

ACCOUNT_COMPANY_FIELDS = {
    "whatsapp_template_invoice_id": "whatsapp_template_invoice",
    "whatsapp_template_payment_id": "whatsapp_template_payment",
    "whatsapp_template_overdue_id": "whatsapp_template_overdue",
}
