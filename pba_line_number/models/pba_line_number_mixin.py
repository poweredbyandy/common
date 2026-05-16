from odoo import api, fields, models


class PbaLineNumberMixin(models.AbstractModel):
    _name = "pba.line.number.mixin"
    _description = "PBA consecutive line number in parent one2many"

    pba_line_number = fields.Integer(
        string="#",
        compute="_compute_pba_line_number",
    )

    @api.model
    def _pba_lines_for_numbering(self, parent, lines_field):
        return parent[lines_field]

    def _pba_assign_line_numbers(self, parents, lines_field):
        line_model = self.env[self._name]
        for parent in parents:
            all_lines = parent[lines_field]
            numbered_lines = line_model._pba_lines_for_numbering(parent, lines_field)
            for index, line in enumerate(numbered_lines, start=1):
                line.pba_line_number = index
            (all_lines - numbered_lines).pba_line_number = 0
