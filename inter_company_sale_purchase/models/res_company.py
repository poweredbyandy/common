from odoo import SUPERUSER_ID, api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    ic_so_from_po = fields.Boolean(
        string="Generate Sales Orders from Purchases",
    )
    ic_po_from_so = fields.Boolean(
        string="Generate Purchase Orders from Sales",
    )
    ic_so_state = fields.Selection(
        selection=[
            ("draft", "Create quotation"),
            ("confirmed", "Create and confirm"),
        ],
        string="Sales Order Automation",
        default="draft",
    )
    ic_po_state = fields.Selection(
        selection=[
            ("draft", "Create RFQ"),
            ("confirmed", "Create and confirm"),
        ],
        string="Purchase Order Automation",
        default="draft",
    )
    ic_picking_mode = fields.Selection(
        selection=[
            ("none", "No synchronization"),
            ("sync_qty", "Synchronize quantities"),
            ("validate", "Synchronize and validate"),
        ],
        string="Picking Automation",
        default="none",
    )
    ic_invoice_mode = fields.Selection(
        selection=[
            ("none", "Do not generate"),
            ("draft", "Create in draft"),
            ("posted", "Create and post"),
        ],
        string="Invoice Automation",
        default="none",
    )
    ic_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Inter-Company User",
        default=SUPERUSER_ID,
        domain=["|", ("active", "=", True), ("id", "=", SUPERUSER_ID)],
        help="User used to create counterpart documents.",
    )
    ic_warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        string="Inter-Company Warehouse",
        compute="_compute_ic_stock_defaults",
        store=True,
        readonly=False,
        domain="[('company_id', '=', id)]",
    )
    ic_receipt_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Inter-Company Receipt Type",
        compute="_compute_ic_stock_defaults",
        store=True,
        readonly=False,
        domain="[('company_id', '=', id), ('code', '=', 'incoming')]",
    )
    ic_purchase_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Inter-Company Purchase Journal",
        compute="_compute_ic_purchase_journal_id",
        store=True,
        readonly=False,
        domain="[('company_id', '=', id), ('type', '=', 'purchase')]",
    )
    ic_block_unshared_product = fields.Boolean(
        string="Block Unshared Products",
        help="Raise an error when a product belongs to a single company.",
    )

    @api.model
    def _find_company_from_partner(self, partner_id):
        if not partner_id:
            return self.browse()
        return self.sudo().search([("partner_id", "parent_of", partner_id)], limit=1)

    @api.depends("ic_so_from_po", "ic_po_from_so")
    def _compute_ic_stock_defaults(self):
        warehouses = dict(
            self.env["stock.warehouse"]._read_group(
                domain=[],
                groupby=["company_id"],
                aggregates=["id:recordset"],
            )
        )
        picking_types = dict(
            self.env["stock.picking.type"]._read_group(
                domain=[("code", "=", "incoming")],
                groupby=["company_id"],
                aggregates=["id:recordset"],
            )
        )
        for company in self:
            if not (company.ic_so_from_po or company.ic_po_from_so):
                company.ic_warehouse_id = False
                company.ic_receipt_type_id = False
                continue
            if not company.ic_warehouse_id:
                whs = warehouses.get(company, self.env["stock.warehouse"])
                company.ic_warehouse_id = whs[:1]
            if not company.ic_receipt_type_id:
                pts = picking_types.get(company, self.env["stock.picking.type"])
                company.ic_receipt_type_id = pts[:1]

    @api.depends("chart_template")
    def _compute_ic_purchase_journal_id(self):
        journals = dict(
            self.env["account.journal"]._read_group(
                domain=[("type", "=", "purchase")],
                groupby=["company_id"],
                aggregates=["id:recordset"],
            )
        )
        for company in self:
            if not company.ic_purchase_journal_id:
                company_journals = journals.get(company, self.env["account.journal"])
                company.ic_purchase_journal_id = company_journals[:1]
