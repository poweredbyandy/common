from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    pba_credit_note_return_picking_type_id = fields.Many2one(
        "stock.picking.type",
        string="Tipo operacion devolucion NC",
        domain="[('code', '=', 'incoming'), '|', ('company_id', '=', False), ('company_id', '=', id)]",
        help="Tipo de operacion de entrada usado al generar el albaran "
        "de devolucion al confirmar una nota de credito.",
    )
