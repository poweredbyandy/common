from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    pba_credit_note_return_picking_type_id = fields.Many2one(
        "stock.picking.type",
        string="Tipo operacion devolucion NC",
        domain="[('code', '=', 'incoming'), '|', ('company_id', '=', False), ('company_id', '=', id)]",
        help="Respaldo si el tipo de operacion de entrega no tiene "
        "configurado su propio tipo de devolucion "
        "(return_picking_type_id). Prioridad: tipo original, luego este.",
    )
