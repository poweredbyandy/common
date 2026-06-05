from odoo import models


class MailWhatsappTemplateVariable(models.Model):
    _inherit = "mail.whatsapp.template.variable"

    def _pba_get_sale_order_for_portal(self, record):
        if record._name == "stock.picking" and record.sale_id:
            return record.sale_id
        if record._name == "account.move":
            sale_orders = record.line_ids.sale_line_ids.order_id
            return sale_orders[:1]
        return super()._pba_get_sale_order_for_portal(record)
