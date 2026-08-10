from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    pba_partner_shipping_id = fields.Many2one(
        "res.partner",
        string="Delivery Address",
        help="Empty means local pickup. When set, deliveries and invoices use this address.",
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_list = list(super()._load_pos_data_fields(config_id))
        if fields_list and "pba_partner_shipping_id" not in fields_list:
            fields_list.append("pba_partner_shipping_id")
        return fields_list

    def _pba_get_shipping_partner(self):
        self.ensure_one()
        return self.pba_partner_shipping_id or self.partner_id

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()
        if self.pba_partner_shipping_id:
            vals["partner_shipping_id"] = self.pba_partner_shipping_id.id
        return vals
