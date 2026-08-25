from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError


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
        help="User used to create counterpart documents. Must belong to this company "
        "and have Sales, Purchase, Inventory and Invoicing access as needed.",
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

    def _ic_ensure_user(self, rights=()):
        """Return the inter-company user after ensuring company + ACL access.

        :param rights: iterable among sale, purchase, account, stock
        """
        self.ensure_one()
        user = self.ic_user_id
        if not user:
            raise UserError(
                _("Provide one user for inter-company relation for %(name)s.", name=self.name)
            )
        user_sudo = user.sudo()
        if self not in user_sudo.company_ids:
            user_sudo.write({"company_ids": [(4, self.id)]})
        if not user_sudo.active and user_sudo.id != SUPERUSER_ID:
            raise UserError(
                _(
                    "Inter-company user %(user)s for company %(company)s is archived.",
                    user=user.display_name,
                    company=self.name,
                )
            )
        group_map = {
            "sale": ("sales_team.group_sale_salesman", _("Sales")),
            "purchase": ("purchase.group_purchase_user", _("Purchase")),
            "account": ("account.group_account_invoice", _("Invoicing")),
            "stock": ("stock.group_stock_user", _("Inventory")),
        }
        missing = []
        for right in rights:
            xmlid, label = group_map[right]
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group and group not in user_sudo.groups_id:
                missing.append(str(label))
        if missing:
            raise UserError(
                _(
                    "Inter-company user %(user)s for company %(company)s is missing access: %(access)s. "
                    "Grant those groups or choose another user.",
                    user=user.display_name,
                    company=self.name,
                    access=", ".join(missing),
                )
            )
        return user

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
