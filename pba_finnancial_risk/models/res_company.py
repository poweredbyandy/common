from odoo import _, api, fields, models


class PbaFinancialRiskGlobalSettings(models.Model):
    _name = "pba.financial.risk.global.settings"
    _description = "Configuracion global de riesgo financiero"

    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id",
        store=False,
        readonly=True,
    )
    pba_effective_currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_pba_effective_currency_id",
        store=False,
    )
    pba_risk_enabled = fields.Boolean(string="Activar riesgo global", default=True)
    pba_risk_credit_currency = fields.Selection(
        selection=[
            ("company", "Company Currency"),
            ("receivable", "Receivable Currency"),
            ("pricelist", "Pricelist Currency"),
            ("manual", "Manual Credit Currency"),
        ],
        string="Divisa de credito global",
        default="company",
    )
    pba_risk_manual_credit_currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Divisa manual global",
    )
    pba_risk_credit_limit = fields.Float(string="Limite de credito global")
    pba_risk_sale_order_include = fields.Boolean(string="Incluir pedidos de venta")
    pba_risk_sale_order_limit = fields.Monetary(
        string="Limite pedidos de venta", currency_field="currency_id"
    )
    pba_risk_invoice_draft_include = fields.Boolean(string="Incluir facturas borrador")
    pba_risk_invoice_draft_limit = fields.Monetary(
        string="Limite facturas borrador", currency_field="currency_id"
    )
    pba_risk_invoice_open_include = fields.Boolean(string="Incluir facturas abiertas")
    pba_risk_invoice_open_limit = fields.Monetary(
        string="Limite facturas abiertas", currency_field="currency_id"
    )
    pba_risk_invoice_unpaid_include = fields.Boolean(string="Incluir facturas vencidas")
    pba_risk_invoice_unpaid_limit = fields.Monetary(
        string="Limite facturas vencidas", currency_field="currency_id"
    )
    pba_risk_account_amount_include = fields.Boolean(string="Incluir otros saldos")
    pba_risk_account_amount_limit = fields.Monetary(
        string="Limite otros saldos", currency_field="currency_id"
    )
    pba_risk_account_amount_unpaid_include = fields.Boolean(
        string="Incluir otros saldos vencidos"
    )
    pba_risk_account_amount_unpaid_limit = fields.Monetary(
        string="Limite otros saldos vencidos", currency_field="currency_id"
    )

    _sql_constraints = [
        (
            "pba_financial_risk_settings_company_uniq",
            "unique(company_id)",
            "Ya existe una configuracion global para esta compania.",
        ),
    ]

    @api.depends(
        "company_id.currency_id",
        "pba_risk_credit_currency",
        "pba_risk_manual_credit_currency_id",
    )
    def _compute_pba_effective_currency_id(self):
        for rec in self:
            if (
                rec.pba_risk_credit_currency == "manual"
                and rec.pba_risk_manual_credit_currency_id
            ):
                rec.pba_effective_currency_id = rec.pba_risk_manual_credit_currency_id
            else:
                rec.pba_effective_currency_id = rec.company_id.currency_id

    @api.model
    def get_or_create_for_company(self, company):
        if not company or not company.id:
            company = self.env.company or self.env.user.company_id
        if not company or not company.id:
            return self.browse()
        settings = self.search([("company_id", "=", company.id)], limit=1)
        if not settings:
            settings = self.create({"company_id": company.id})
        return settings

    def _get_partner_global_risk_vals(self):
        self.ensure_one()
        include_value = bool(self.pba_risk_enabled)
        return {
            "credit_currency": self.pba_risk_credit_currency,
            "manual_credit_currency_id": self.pba_risk_manual_credit_currency_id.id
            if self.pba_risk_credit_currency == "manual"
            else False,
            "credit_limit": self.pba_risk_credit_limit,
            "risk_sale_order_include": include_value and self.pba_risk_sale_order_include,
            "risk_sale_order_limit": self.pba_risk_sale_order_limit,
            "risk_invoice_draft_include": include_value
            and self.pba_risk_invoice_draft_include,
            "risk_invoice_draft_limit": self.pba_risk_invoice_draft_limit,
            "risk_invoice_open_include": include_value
            and self.pba_risk_invoice_open_include,
            "risk_invoice_open_limit": self.pba_risk_invoice_open_limit,
            "risk_invoice_unpaid_include": include_value
            and self.pba_risk_invoice_unpaid_include,
            "risk_invoice_unpaid_limit": self.pba_risk_invoice_unpaid_limit,
            "risk_account_amount_include": include_value
            and self.pba_risk_account_amount_include,
            "risk_account_amount_limit": self.pba_risk_account_amount_limit,
            "risk_account_amount_unpaid_include": include_value
            and self.pba_risk_account_amount_unpaid_include,
            "risk_account_amount_unpaid_limit": self.pba_risk_account_amount_unpaid_limit,
        }

    def _get_risk_partners_domain(self):
        self.ensure_one()
        return [
            "|",
            ("company_id", "=", False),
            ("company_id", "=", self.company_id.id),
            "|",
            ("is_company", "=", True),
            ("parent_id", "=", False),
        ]

    def _get_partners_with_assigned_limits(self, partners):
        return partners.filtered(
            lambda p: any(
                [
                    p.credit_limit,
                    p.risk_invoice_draft_limit,
                    p.risk_invoice_open_limit,
                    p.risk_invoice_unpaid_limit,
                    p.risk_account_amount_limit,
                    p.risk_account_amount_unpaid_limit,
                    p.risk_sale_order_limit,
                ]
            )
        )

    def action_apply_global_risk_to_partners(self):
        self.ensure_one()
        partners = self.env["res.partner"].search(self._get_risk_partners_domain())
        partners_with_limits = self._get_partners_with_assigned_limits(partners)
        if (
            partners_with_limits
            and not self.env.context.get("pba_confirm_update_existing")
            and not self.env.context.get("pba_skip_existing")
        ):
            wizard = self.env["pba.financial.risk.apply.confirm.wizard"].create(
                {
                    "settings_id": self.id,
                    "affected_count": len(partners_with_limits),
                }
            )
            return {
                "type": "ir.actions.act_window",
                "name": _("Confirmar actualizacion"),
                "res_model": "pba.financial.risk.apply.confirm.wizard",
                "res_id": wizard.id,
                "view_mode": "form",
                "target": "new",
            }
        if self.env.context.get("pba_skip_existing"):
            partners = partners - partners_with_limits
        if partners:
            partners.write(self._get_partner_global_risk_vals())
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Riesgo financiero"),
                "message": _("Se actualizaron %(count)s contactos.", count=len(partners)),
                "type": "success",
                "sticky": False,
            },
        }
