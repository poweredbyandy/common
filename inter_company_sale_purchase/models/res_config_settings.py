from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ic_so_from_po = fields.Boolean(
        related="company_id.ic_so_from_po",
        readonly=False,
    )
    ic_po_from_so = fields.Boolean(
        related="company_id.ic_po_from_so",
        readonly=False,
    )
    ic_so_state = fields.Selection(
        related="company_id.ic_so_state",
        readonly=False,
    )
    ic_po_state = fields.Selection(
        related="company_id.ic_po_state",
        readonly=False,
    )
    ic_picking_mode = fields.Selection(
        related="company_id.ic_picking_mode",
        readonly=False,
    )
    ic_invoice_mode = fields.Selection(
        related="company_id.ic_invoice_mode",
        readonly=False,
    )
    ic_user_id = fields.Many2one(
        related="company_id.ic_user_id",
        readonly=False,
    )
    ic_warehouse_id = fields.Many2one(
        related="company_id.ic_warehouse_id",
        readonly=False,
    )
    ic_receipt_type_id = fields.Many2one(
        related="company_id.ic_receipt_type_id",
        readonly=False,
    )
    ic_purchase_journal_id = fields.Many2one(
        related="company_id.ic_purchase_journal_id",
        readonly=False,
    )
    ic_block_unshared_product = fields.Boolean(
        related="company_id.ic_block_unshared_product",
        readonly=False,
    )
    ic_allow_confirm_ic_purchase = fields.Boolean(
        related="company_id.ic_allow_confirm_ic_purchase",
        readonly=False,
    )
