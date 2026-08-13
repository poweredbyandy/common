from odoo import api, fields, models, _

BUS_NOTIFICATION_TYPE = "pba.stock.picking/available"


class StockPicking(models.Model):
    _inherit = "stock.picking"

    pba_barcode_sale_name = fields.Char(
        string="Pedido",
        compute="_compute_pba_barcode_kanban_info",
    )
    pba_barcode_invoice_payment_state = fields.Selection(
        selection=[
            ("none", "Sin factura"),
            ("not_paid", "No pagada"),
            ("partial", "Parcialmente pagada"),
            ("paid", "Pagada"),
        ],
        string="Estado de pago factura",
        compute="_compute_pba_barcode_kanban_info",
    )
    pba_barcode_invoice_payment_label = fields.Char(
        string="Etiqueta de pago",
        compute="_compute_pba_barcode_kanban_info",
    )
    pba_barcode_payment_term_label = fields.Char(
        string="Termino de pago",
        compute="_compute_pba_barcode_kanban_info",
    )
    pba_barcode_kanban_tone = fields.Selection(
        selection=[
            ("immediate_unpaid", "Inmediato no pagado"),
            ("credit", "Credito"),
        ],
        string="Tono kanban barcode",
        compute="_compute_pba_barcode_kanban_info",
    )
    pba_barcode_partner_vat = fields.Char(
        string="VAT",
        compute="_compute_pba_barcode_kanban_info",
    )

    @api.model_create_multi
    def create(self, vals_list):
        pickings = super().create(vals_list)
        pickings._pba_notify_barcode_available()
        return pickings

    def action_assign(self):
        result = super().action_assign()
        self._pba_notify_barcode_available()
        return result

    def _pba_barcode_related_invoices(self):
        self.ensure_one()
        invoices = self.sale_id.invoice_ids
        if "invoice_ids" in self._fields:
            invoices |= self.invoice_ids
        return invoices.filtered(
            lambda inv: inv.state == "posted"
            and inv.move_type in ("out_invoice", "out_refund")
        )

    def _pba_payment_term_is_immediate(self, term):
        if not term:
            return True
        return all(not line.nb_days for line in term.line_ids)

    def _pba_barcode_kanban_tone(self, term, payment_state):
        if not self._pba_payment_term_is_immediate(term):
            return "credit"
        if payment_state == "paid":
            return False
        return "immediate_unpaid"

    @api.depends(
        "sale_id",
        "sale_id.name",
        "sale_id.payment_term_id",
        "sale_id.payment_term_id.name",
        "sale_id.payment_term_id.line_ids.nb_days",
        "sale_id.invoice_ids.state",
        "sale_id.invoice_ids.payment_state",
        "sale_id.invoice_ids.amount_residual",
        "sale_id.invoice_ids.move_type",
        "sale_id.invoice_ids.invoice_payment_term_id",
        "sale_id.invoice_ids.invoice_payment_term_id.name",
        "sale_id.invoice_ids.invoice_payment_term_id.line_ids.nb_days",
        "partner_id",
        "partner_id.vat",
    )
    def _compute_pba_barcode_kanban_info(self):
        for picking in self:
            sale = picking.sale_id
            picking.pba_barcode_partner_vat = picking.partner_id.vat or False
            sale_vat_lines = []
            if sale.name:
                sale_vat_lines.append("%s %s" % (_("Pedido:"), sale.name))
            if picking.pba_barcode_partner_vat:
                sale_vat_lines.append(
                    "%s %s" % (_("VAT:"), picking.pba_barcode_partner_vat)
                )
            picking.pba_barcode_sale_name = "\n".join(sale_vat_lines) or False
            if not sale and not (
                "invoice_ids" in picking._fields and picking.invoice_ids
            ):
                picking.pba_barcode_payment_term_label = False
                picking.pba_barcode_invoice_payment_state = False
                picking.pba_barcode_invoice_payment_label = False
                picking.pba_barcode_kanban_tone = False
                continue
            invoices = picking._pba_barcode_related_invoices()
            term = sale.payment_term_id or invoices[:1].invoice_payment_term_id
            if term:
                term_label = term.display_name
                if not picking._pba_payment_term_is_immediate(term):
                    term_label = "\u2060%s" % term_label
                picking.pba_barcode_payment_term_label = term_label
            elif sale:
                picking.pba_barcode_payment_term_label = _("De Contado")
            else:
                picking.pba_barcode_payment_term_label = False
            if not invoices:
                state = "none"
                label = _("Sin factura")
            else:
                paid = all(
                    inv.currency_id.is_zero(inv.amount_residual)
                    or inv.payment_state in ("paid", "reversed", "in_payment")
                    for inv in invoices
                )
                unpaid = all(
                    not inv.currency_id.is_zero(inv.amount_residual)
                    and inv.currency_id.compare_amounts(
                        inv.amount_residual, inv.amount_total
                    )
                    >= 0
                    and inv.payment_state == "not_paid"
                    for inv in invoices
                )
                if paid:
                    state = "paid"
                    label = _("Pagada")
                elif unpaid:
                    state = "not_paid"
                    label = _("No pagada")
                else:
                    state = "partial"
                    label = _("Parcialmente pagada")
            picking.pba_barcode_invoice_payment_state = state
            picking.pba_barcode_invoice_payment_label = label
            picking.pba_barcode_kanban_tone = picking._pba_barcode_kanban_tone(
                term, state
            )

    @api.model
    def _pba_bus_barcode_reload(self, picking_type_id=False):
        if self.env.context.get("install_mode"):
            return
        group = self.env.ref("stock.group_stock_user", raise_if_not_found=False)
        if not group:
            return
        group._bus_send(
            BUS_NOTIFICATION_TYPE,
            {
                "picking_id": False,
                "picking_type_id": picking_type_id or False,
            },
        )

    def _pba_notify_barcode_available(self):
        if self.env.context.get("install_mode"):
            return
        pickings = self.filtered(
            lambda picking: picking.state in ("assigned", "confirmed", "waiting")
        )
        if not pickings:
            self._pba_bus_barcode_reload()
            return
        group = self.env.ref("stock.group_stock_user", raise_if_not_found=False)
        if not group:
            return
        for picking_type_id in set(pickings.picking_type_id.ids):
            group._bus_send(
                BUS_NOTIFICATION_TYPE,
                {
                    "picking_id": False,
                    "picking_type_id": picking_type_id,
                },
            )
