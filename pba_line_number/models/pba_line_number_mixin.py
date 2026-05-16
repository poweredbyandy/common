from odoo import fields, models


class PbaLineNumberMixin(models.AbstractModel):
    _name = "pba.line.number.mixin"
    _description = "PBA consecutive line number in parent one2many"

    pba_line_number = fields.Integer(
        string="#",
        compute="_compute_pba_line_number",
    )

    def _pba_assign_line_numbers(self, parents, lines_field):
        for parent in parents:
            for index, line in enumerate(parent[lines_field].sorted("sequence"), start=1):
                line.pba_line_number = index
