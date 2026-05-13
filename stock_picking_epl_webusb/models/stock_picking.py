# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    dispatch_bultos_manual = fields.Integer(
        string="Bultos (sin empaquetar)",
        default=0,
        copy=False,
        help="Si no hay paquetes destino en las operaciones, indique cuántas etiquetas EPL/ZPL desea imprimir por WebUSB.",
    )

    @api.constrains("dispatch_bultos_manual")
    def _check_dispatch_bultos_manual(self):
        for picking in self:
            if picking.dispatch_bultos_manual < 0:
                raise ValidationError(_("Los bultos manuales no pueden ser negativos."))

    def _epl_label_scan_text(self):
        self.ensure_one()
        if "barcode" in self._fields:
            bc = (self.barcode or "").strip()
            if bc:
                return bc
        return (self.name or "").strip()
