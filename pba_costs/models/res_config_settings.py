from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

from .pba_constants import DEFAULT_PBA_FINAL_COST_FORMULA, pba_final_cost_dummy_eval_context


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pba_final_cost_formula = fields.Text(
        string="Fórmula global del costo final (PBA)",
        help="Expresión evaluada (safe_eval) para cada plantilla de producto. "
        "Variables disponibles (monedas y porcentajes como float en la UdM/moneda de la plantilla):\n"
        "• pba_last_cost — último costo de compra (tras descuento comercial)\n"
        "• pba_cost_discount, pba_cost_discount_percent — descuento de costo sobre ese remanente\n"
        "• pba_cost_freight, pba_cost_tariff, pba_cost_operative, pba_cost_nationalization "
        "(importes = (pba_last_cost − pba_cost_discount) × %)\n"
        "• pba_cost_*_percent por cada bloque (freight, tariff, operative, nationalization)\n"
        "• En fórmulas antiguas, pba_cost_*_operation_total es el remanente tras descuento de costo.\n"
        "• standard_price — costo promedio (estándar) Odoo\n"
        "• list_price — precio de venta\n"
        "Operadores: + - * / ** y paréntesis. Funciones: min, max, abs, round, sum, etc. "
        "Los porcentajes pba_*_percent van en escala 0–1 (0,10 = 10%).\n"
        "Ejemplo por defecto: (pba_last_cost - pba_cost_discount) + pba_cost_freight + "
        "pba_cost_tariff + pba_cost_operative + pba_cost_nationalization\n"
        "También puede editarse en la ficha del producto (pestaña Costos) para usuarios con grupo Características técnicas.",
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        icp = self.env["ir.config_parameter"].sudo()
        res["pba_final_cost_formula"] = icp.get_param(
            "pba_costs.final_cost_formula",
            DEFAULT_PBA_FINAL_COST_FORMULA,
        )
        return res

    def set_values(self):
        super().set_values()
        if not self.env.user.has_group("base.group_system"):
            return
        formula = (self.pba_final_cost_formula or "").strip()
        if not formula:
            formula = DEFAULT_PBA_FINAL_COST_FORMULA
        try:
            safe_eval(formula, pba_final_cost_dummy_eval_context())
        except Exception as err:
            raise UserError(
                _("La fórmula no es válida: %s") % (err,)
            ) from err
        self.env["ir.config_parameter"].sudo().set_param(
            "pba_costs.final_cost_formula",
            formula,
        )
        self.env["product.template"].invalidate_model(
            ["pba_final_cost", "pba_final_cost_formula_edit"]
        )
