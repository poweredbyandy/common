import operator
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    goal_commission_currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Moneda Meta Comision",
        default=lambda self: self.env.company.currency_id.id,
    )
    goal_commission_tier_ids = fields.One2many(
        comodel_name="goal.commission.tier",
        inverse_name="partner_id",
        string="Tramos de Comision",
    )
    goal_commission_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Producto de Comision por Meta",
        domain=[("type", "=", "service")],
    )
    goal_commission_excluded_journal_ids = fields.Many2many(
        comodel_name="account.journal",
        string="Diarios Excluidos para Comision",
    )
    goal_commission_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Diario de Comision",
        domain="[('type', '=', 'purchase')]",
    )
    is_goal_commission_seller = fields.Boolean(
        compute="_compute_is_goal_commission_seller",
    )
    show_goal_commission_tab = fields.Boolean(
        compute="_compute_is_goal_commission_seller",
    )
    goal_commission_pending_invoice_count = fields.Integer(
        string="Facturas Pendientes",
        compute="_compute_goal_commission_stats",
        store=False,
        search="_search_goal_commission_pending_invoice_count",
    )
    goal_commission_pending_display = fields.Char(
        string="Total Pendiente",
        compute="_compute_goal_commission_stats",
        store=False,
    )
    goal_invoice_amount = fields.Monetary(
        string="Facturado",
        currency_field="goal_commission_currency_id",
        compute="_compute_goal_progress",
        store=False,
    )
    goal_collected_amount = fields.Monetary(
        string="Cobrado",
        currency_field="goal_commission_currency_id",
        compute="_compute_goal_progress",
        store=False,
    )
    goal_commission_target_amount = fields.Monetary(
        string="Meta",
        currency_field="goal_commission_currency_id",
        compute="_compute_goal_progress",
        store=False,
    )
    goal_invoice_progress_pct = fields.Float(
        string="Progreso Facturado",
        compute="_compute_goal_progress",
        store=False,
    )
    goal_invoice_progress_display = fields.Char(
        string="Progreso Facturado (%)",
        compute="_compute_goal_progress",
        store=False,
    )
    goal_collection_progress_pct = fields.Float(
        string="Progreso Cobro",
        compute="_compute_goal_progress",
        store=False,
    )
    goal_collected_target_progress_pct = fields.Float(
        string="Progreso Cobrado vs Meta",
        compute="_compute_goal_progress",
        store=False,
    )
    goal_collection_progress_display = fields.Char(
        string="Progreso Cobro (%)",
        compute="_compute_goal_progress",
        store=False,
    )
    goal_collected_target_progress_display = fields.Char(
        string="Progreso Cobrado vs Meta (%)",
        compute="_compute_goal_progress",
        store=False,
    )
    goal_commission_current_percent = fields.Float(
        string="% Comision Actual",
        compute="_compute_goal_progress",
        store=False,
    )
    goal_commission_current_tier_name = fields.Char(
        string="Tramo actual",
        compute="_compute_goal_progress",
        store=False,
    )
    goal_commission_current_tier_target = fields.Monetary(
        string="Tope tramo actual",
        currency_field="goal_commission_currency_id",
        compute="_compute_goal_progress",
        store=False,
    )
    goal_invoice_tier_progress_pct = fields.Float(
        string="Progreso en tramo actual",
        compute="_compute_goal_progress",
        store=False,
    )
    goal_invoice_tier_progress_display = fields.Char(
        string="Progreso tramo actual (%)",
        compute="_compute_goal_progress",
        store=False,
    )
    goal_tier_achievement_display = fields.Char(
        string="Metas cumplidas",
        compute="_compute_goal_progress",
        store=False,
    )
    goal_tier_badges_html = fields.Html(
        string="Estado de metas",
        compute="_compute_goal_progress",
        sanitize=False,
        store=False,
    )
    goal_achieved_tier_count = fields.Integer(
        string="Metas cumplidas (cant.)",
        compute="_compute_goal_progress",
        store=False,
    )
    goal_dashboard_period_name = fields.Char(
        string="Periodo Dashboard",
        compute="_compute_goal_dashboard_period_name",
    )

    @api.model
    def _get_goal_commission_period_from_context(self, company=None):
        period_id = self.env.context.get("goal_commission_period_id")
        if period_id:
            period = self.env["goal.commission.period"].browse(period_id).exists()
            if period:
                return period
        company = company or self.env.company
        return self.env["goal.commission.period"]._get_default_period(company)

    @api.depends_context("goal_commission_period_id")
    def _compute_goal_dashboard_period_name(self):
        for partner in self:
            period = partner._get_goal_commission_period_from_context()
            partner.goal_dashboard_period_name = period.name if period else ""

    def _get_goal_payable_period_domain(self, period):
        if not period:
            return []
        return [
            ("goal_commission_payable_date", ">=", period.date_start),
            ("goal_commission_payable_date", "<=", period.date_end),
        ]

    def _get_goal_invoice_domain(self, users, period, start_date):
        domain = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("invoice_user_id", "in", users.ids),
        ]
        if period:
            domain.extend([
                ("invoice_date", ">=", period.date_start),
                ("invoice_date", "<=", period.date_end),
            ])
        elif start_date:
            domain.append(("invoice_date", ">=", start_date))
        return domain

    def _get_goal_invoiced_amount_for_period(self, period):
        self.ensure_one()
        if not period:
            return 0.0
        users = self._get_goal_commission_seller_users()
        if not users:
            return 0.0
        company = self._get_goal_reference_company()
        goal_currency = self.goal_commission_currency_id or company.currency_id
        invoices = self.env["account.move"].search(self._get_goal_invoice_domain(users, period, False))
        total_invoiced = 0.0
        dashboard = self._goal_commission_dashboard()
        for invoice in invoices:
            inv_date = invoice.invoice_date or invoice.date
            if not inv_date:
                continue
            if not dashboard._goal_commission_invoice_eligible_for_progress(invoice, inv_date):
                continue
            total_invoiced += invoice._goal_commission_net_subtotal_in_currency(goal_currency)
        currency = self.goal_commission_currency_id or company.currency_id
        return currency.round(total_invoiced)

    @api.depends(
        "user_ids",
        "user_ids.share",
        "user_ids.active",
        "goal_commission_tier_ids",
        "goal_commission_tier_ids.active",
    )
    def _compute_is_goal_commission_seller(self):
        is_admin = self.env.user.has_group("pba_goal_commision.group_goal_commission_admin")
        for partner in self:
            has_internal_user = bool(partner.user_ids.filtered(lambda user: not user.share and user.active))
            has_active_tier = bool(partner.goal_commission_tier_ids.filtered("active"))
            partner.show_goal_commission_tab = has_internal_user or is_admin
            partner.is_goal_commission_seller = has_internal_user and has_active_tier

    def _get_goal_commission_seller_users(self):
        self.ensure_one()
        return self.user_ids.filtered(lambda user: not user.share and user.active)

    def _get_goal_reference_company(self):
        self.ensure_one()
        users = self._get_goal_commission_seller_users()
        return users[:1].company_id if users else self.env.company

    def _goal_commission_dashboard(self):
        return self.env["goal.commission.dashboard.mixin"]

    def _get_goal_commission_percent_for_amount(self, amount_in_goal_currency):
        tier = self._get_goal_commission_tier_for_amount(amount_in_goal_currency)
        return tier.commission_percent if tier else 0.0

    def _get_goal_commission_tier_for_amount(self, amount_in_goal_currency):
        self.ensure_one()
        tiers = self.goal_commission_tier_ids.filtered("active").sorted(
            key=lambda tier: (tier.sequence, tier.min_amount, tier.id)
        )
        matched = tiers.filtered(
            lambda tier: amount_in_goal_currency >= tier.min_amount
            and (not tier.max_amount or amount_in_goal_currency < tier.max_amount)
        )
        if matched:
            return matched[-1]
        upper_tiers = tiers.filtered(
            lambda tier: tier.max_amount and amount_in_goal_currency >= tier.max_amount
        )
        if upper_tiers:
            return upper_tiers[-1]
        return self.env["goal.commission.tier"]

    def _get_goal_target_for_amount(self, amount_in_goal_currency):
        self.ensure_one()
        tiers = self.goal_commission_tier_ids.filtered("active").sorted(
            key=lambda tier: (tier.sequence, tier.min_amount, tier.id)
        )
        if not tiers:
            return 0.0
        matched = tiers.filtered(
            lambda tier: amount_in_goal_currency >= tier.min_amount
            and (not tier.max_amount or amount_in_goal_currency < tier.max_amount)
        )
        if matched:
            tier = matched[-1]
            return tier.max_amount or amount_in_goal_currency
        higher_tiers = tiers.filtered(lambda tier: tier.min_amount > amount_in_goal_currency)
        if higher_tiers:
            return higher_tiers[0].max_amount or higher_tiers[0].min_amount
        return tiers[-1].max_amount or amount_in_goal_currency

    def _get_goal_tier_status_list(self, invoiced_amount):
        self.ensure_one()
        tiers = self.goal_commission_tier_ids.filtered("active").sorted(
            key=lambda tier: (tier.sequence, tier.min_amount, tier.id)
        )
        current_tier = self._get_goal_commission_tier_for_amount(invoiced_amount)
        status_list = []
        for tier in tiers:
            if tier.max_amount and invoiced_amount >= tier.max_amount:
                state = "achieved"
                progress_pct = 100.0
            elif tier == current_tier:
                state = "current"
                progress_pct, _target = self._get_current_tier_progress(invoiced_amount, tier)
            else:
                state = "pending"
                progress_pct = 0.0
            status_list.append(
                {
                    "tier": tier,
                    "name": tier.name,
                    "state": state,
                    "min_amount": tier.min_amount,
                    "max_amount": tier.max_amount,
                    "commission_percent": tier.commission_percent,
                    "progress_pct": progress_pct,
                }
            )
        return status_list

    def _get_current_tier_progress(self, invoiced_amount, tier):
        self.ensure_one()
        if not tier:
            return 0.0, 0.0
        if tier.max_amount:
            band = tier.max_amount - tier.min_amount
            if band <= 0:
                return 100.0, tier.max_amount
            progress = ((invoiced_amount - tier.min_amount) / band) * 100.0
            return min(100.0, max(0.0, progress)), tier.max_amount
        if tier.min_amount:
            progress = (invoiced_amount / tier.min_amount) * 100.0 if tier.min_amount else 0.0
            return min(100.0, max(0.0, progress)), invoiced_amount
        return 0.0, 0.0

    def _format_goal_tier_achievement_display(self, status_list):
        parts = []
        for row in status_list:
            if row["state"] == "achieved":
                parts.append("✓ %s" % row["name"])
            elif row["state"] == "current":
                parts.append("▶ %s (%.0f%%)" % (row["name"], row["progress_pct"]))
            else:
                parts.append("○ %s" % row["name"])
        return " · ".join(parts) if parts else "—"

    def _format_goal_tier_badges_html(self, status_list):
        badges = []
        for row in status_list:
            name = row["name"]
            if row["state"] == "achieved":
                badges.append(
                    '<span class="badge rounded-pill text-bg-success me-1 mb-1" title="Meta cumplida">'
                    "✓ %s</span>" % name
                )
            elif row["state"] == "current":
                badges.append(
                    '<span class="badge rounded-pill text-bg-primary me-1 mb-1" title="Tramo en curso">'
                    "▶ %s %.0f%%</span>" % (name, row["progress_pct"])
                )
            else:
                badges.append(
                    '<span class="badge rounded-pill text-bg-light text-muted border me-1 mb-1" title="Meta pendiente">'
                    "○ %s</span>" % name
                )
        return "".join(badges)

    def _get_goal_pending_commission_invoices(self):
        self.ensure_one()
        users = self._get_goal_commission_seller_users()
        if not users:
            return self.env["account.move"]
        period = self._get_goal_commission_period_from_context()
        domain = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("invoice_user_id", "in", users.ids),
            ("goal_commission_collectible", "=", True),
        ]
        if period:
            domain.extend(self._get_goal_payable_period_domain(period))
        return self.env["account.move"].search(domain)

    def _get_goal_commission_other_periods_summary(self, current_period=None):
        self.ensure_one()
        users = self._get_goal_commission_seller_users()
        if not users:
            return []
        current_period = current_period or self._get_goal_commission_period_from_context()
        domain = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("invoice_user_id", "in", users.ids),
            ("goal_commission_collectible", "=", True),
        ]
        all_invoices = self.env["account.move"].search(domain)
        if current_period:
            other_invoices = all_invoices.filtered_domain(
                [
                    "|",
                    ("goal_commission_payable_date", "<", current_period.date_start),
                    ("goal_commission_payable_date", ">", current_period.date_end),
                ]
            )
        else:
            other_invoices = all_invoices
        Period = self.env["goal.commission.period"]
        grouped = {}
        for invoice in other_invoices:
            payable_date = invoice.goal_commission_payable_date
            if not payable_date:
                continue
            period = Period._get_period_for_date(payable_date, invoice.company_id)
            period_key = period.id if period else 0
            if period_key not in grouped:
                grouped[period_key] = {
                    "period_name": period.name if period else _("Sin periodo"),
                    "invoice_count": 0,
                    "totals": {},
                }
            grouped[period_key]["invoice_count"] += 1
            preview = invoice.prepare_goal_commission_preview_data()
            currency = preview["currency"]
            grouped[period_key]["totals"][currency] = (
                grouped[period_key]["totals"].get(currency, 0.0) + preview["amount"]
            )
        return sorted(
            grouped.values(),
            key=lambda row: row["period_name"],
        )

    @api.depends_context("goal_commission_period_id")
    @api.depends("user_ids", "user_ids.active")
    def _compute_goal_commission_stats(self):
        partners = self.filtered(lambda partner: partner._get_goal_commission_seller_users())
        (self - partners).goal_commission_pending_invoice_count = 0
        (self - partners).goal_commission_pending_display = "—"
        if not partners:
            return
        period = partners._get_goal_commission_period_from_context()
        user_ids = partners.mapped("user_ids").filtered(lambda user: not user.share and user.active).ids
        if not user_ids:
            return
        domain = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("invoice_user_id", "in", user_ids),
            ("goal_commission_collectible", "=", True),
        ]
        if period:
            domain.extend(partners._get_goal_payable_period_domain(period))
        Move = self.env["account.move"]
        users = self.env["res.users"].browse(user_ids)
        user_partner = {user.id: user.partner_id.id for user in users}
        partner_ids = set(partners.ids)
        count_groups = Move.read_group(domain, [], ["invoice_user_id"], lazy=False)
        count_by_partner = defaultdict(int)
        for group in count_groups:
            user_data = group.get("invoice_user_id")
            if not user_data:
                continue
            partner_id = user_partner.get(user_data[0])
            if partner_id in partner_ids:
                count_by_partner[partner_id] += group.get("__count", group.get("invoice_user_id_count", 0))
        amount_groups = Move.read_group(
            domain,
            ["goal_commission_pending_total:sum"],
            ["invoice_user_id", "currency_id"],
            lazy=False,
        )
        totals_by_partner = defaultdict(lambda: defaultdict(float))
        currencies = {}
        for group in amount_groups:
            user_data = group.get("invoice_user_id")
            currency_data = group.get("currency_id")
            if not user_data or not currency_data:
                continue
            partner_id = user_partner.get(user_data[0])
            if partner_id not in partner_ids:
                continue
            currency_id = currency_data[0]
            currencies[currency_id] = self.env["res.currency"].browse(currency_id)
            totals_by_partner[partner_id][currency_id] += group["goal_commission_pending_total"]
        for partner in partners:
            currency_totals = totals_by_partner.get(partner.id)
            if not currency_totals:
                partner.goal_commission_pending_invoice_count = 0
                partner.goal_commission_pending_display = "—"
                continue
            partner.goal_commission_pending_invoice_count = count_by_partner.get(partner.id, 0)
            partner.goal_commission_pending_display = " · ".join(
                "%s %s" % ("{:,.2f}".format(amount), currencies[currency_id].name)
                for currency_id, amount in sorted(currency_totals.items(), key=lambda row: currencies[row[0]].name)
            )

    def _search_goal_commission_pending_invoice_count(self, operator_symbol, value):
        supported = {
            ">": operator.gt,
            ">=": operator.ge,
            "=": operator.eq,
            "!=": operator.ne,
            "<": operator.lt,
            "<=": operator.le,
        }
        if operator_symbol not in supported:
            return [("id", "=", 0)]
        compare = supported[operator_symbol]
        period = self._get_goal_commission_period_from_context()
        domain = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("goal_commission_collectible", "=", True),
            ("invoice_user_id", "!=", False),
        ]
        if period:
            domain.extend(self._get_goal_payable_period_domain(period))
        invoices = self.env["account.move"].search(domain)
        counts = {}
        for invoice in invoices:
            partner = invoice.invoice_user_id.partner_id
            if not partner:
                continue
            counts[partner.id] = counts.get(partner.id, 0) + 1
        partners = self.search([("user_ids", "!=", False), ("goal_commission_tier_ids", "!=", False)])
        matched_ids = []
        for partner in partners:
            if compare(counts.get(partner.id, 0), value):
                matched_ids.append(partner.id)
        return [("id", "in", matched_ids)] if matched_ids else [("id", "=", 0)]

    @api.depends_context("goal_commission_period_id")
    @api.depends(
        "user_ids",
        "user_ids.active",
        "goal_commission_currency_id",
        "goal_commission_tier_ids",
        "goal_commission_tier_ids.name",
        "goal_commission_tier_ids.min_amount",
        "goal_commission_tier_ids.max_amount",
        "goal_commission_tier_ids.commission_percent",
        "company_id.goal_commission_start_date",
    )
    def _compute_goal_progress(self):
        self._goal_commission_dashboard()._goal_commission_reset_progress_fields(self)
        partners = self.filtered(lambda partner: partner._get_goal_commission_seller_users())
        if not partners:
            return
        period = partners._get_goal_commission_period_from_context()
        users = partners.mapped("user_ids").filtered(lambda user: not user.share and user.active)
        if not users:
            return
        start_date = False
        if not period:
            companies = partners.mapped("company_id") | partners._get_goal_reference_company()
            start_dates = [company.goal_commission_start_date for company in companies if company.goal_commission_start_date]
            start_date = min(start_dates) if start_dates else False
        domain = self._goal_commission_dashboard()._goal_commission_invoice_progress_domain(
            users.ids, period, start_date
        )
        invoices = self.env["account.move"].search(domain)
        if not invoices:
            return
        users = self.env["res.users"].browse(users.ids)
        user_partner = {user.id: user.partner_id.id for user in users}
        partner_by_id = {partner.id: partner for partner in partners}
        totals_by_partner = {}
        for invoice in invoices:
            partner_id = user_partner.get(invoice.invoice_user_id.id)
            partner = partner_by_id.get(partner_id)
            if not partner:
                continue
            inv_date = invoice.invoice_date or invoice.date
            if not inv_date:
                continue
            if not self._goal_commission_dashboard()._goal_commission_invoice_eligible_for_progress(
                invoice, inv_date
            ):
                continue
            company = partner._get_goal_reference_company()
            goal_currency = partner.goal_commission_currency_id or company.currency_id
            invoiced_amount = invoice._goal_commission_net_subtotal_in_currency(goal_currency)
            if not invoiced_amount:
                continue
            totals = totals_by_partner.setdefault(
                partner_id,
                {"invoiced": 0.0, "collected": 0.0, "currency": goal_currency},
            )
            totals["invoiced"] += invoiced_amount
            if invoice.payment_state in ("paid", "in_payment", "partial"):
                collected_amount = invoice._goal_commission_collected_subtotal_in_currency(goal_currency)
                if collected_amount:
                    totals["collected"] += collected_amount
        self._goal_commission_dashboard()._goal_commission_apply_progress_totals(
            partners, totals_by_partner
        )

    def get_goal_pending_commission_report_data(self):
        self.ensure_one()
        invoices_data = []
        totals = {}
        for invoice in self._get_goal_pending_commission_invoices():
            preview = invoice.prepare_goal_commission_preview_data()
            preview["invoice"] = invoice
            invoices_data.append(preview)
            totals[preview["currency"]] = totals.get(preview["currency"], 0.0) + preview["amount"]
        return {
            "invoices": invoices_data,
            "invoice_count": len(invoices_data),
            "totals": [{"currency": currency, "amount": amount} for currency, amount in sorted(totals.items())],
            "has_data": bool(invoices_data),
        }

    def action_pay_goal_pending_commissions(self):
        self.ensure_one()
        period = self._get_goal_commission_period_from_context()
        invoices = self._get_goal_pending_commission_invoices()
        if not invoices:
            if period:
                other_summary = self._get_goal_commission_other_periods_summary(period)
                if other_summary:
                    lines = []
                    for row in other_summary:
                        totals = " · ".join(
                            "{:,.2f} {}".format(amount, currency)
                            for currency, amount in sorted(row["totals"].items())
                        )
                        lines.append(
                            _("%(period)s: %(count)s factura(s) (%(totals)s)")
                            % {
                                "period": row["period_name"],
                                "count": row["invoice_count"],
                                "totals": totals,
                            }
                        )
                    raise UserError(
                        _(
                            "No hay comisiones pendientes en el periodo %(period)s.\n\n"
                            "Tienes comisiones sin pagar en otros periodos:\n%(details)s\n\n"
                            "Cambia el periodo en el dashboard para pagarlas."
                        )
                        % {"period": period.name, "details": "\n".join(lines)}
                    )
            raise UserError(_("No hay comisiones pendientes para facturar a este vendedor."))
        context = {
            "default_invoice_ids": [(6, 0, invoices.ids)],
            "default_partner_id": self.id,
        }
        if period:
            context["default_period_id"] = period.id
        return {
            "name": _("Pagar Comisiones"),
            "type": "ir.actions.act_window",
            "res_model": "goal.commission.billing.wizard",
            "view_mode": "form",
            "target": "new",
            "context": context,
        }

    def action_open_goal_pending_commissions(self):
        self.ensure_one()
        users = self._get_goal_commission_seller_users()
        period = self._get_goal_commission_period_from_context()
        domain = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("invoice_user_id", "in", users.ids),
            ("goal_commission_collectible", "=", True),
        ]
        if period:
            domain.extend(self._get_goal_payable_period_domain(period))
        context = {"default_move_type": "out_invoice"}
        if period:
            context["goal_commission_period_id"] = period.id
        return {
            "name": _("Comisiones Pendientes"),
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": domain,
            "context": context,
        }

    def action_print_goal_pending_commissions(self):
        self.ensure_one()
        if not self._get_goal_pending_commission_invoices():
            raise UserError(_("No hay comisiones pendientes para imprimir."))
        return self.env.ref("pba_goal_commision.action_report_goal_commission_pending").report_action(self)

    @api.model
    def action_goal_commission_dashboard_menu(self):
        period_model = self.env["goal.commission.period"]
        if not period_model.search([("company_id", "in", self.env.companies.ids)], limit=1):
            period_model.sync_from_invoices()
        xmlid = (
            "pba_goal_commision.action_goal_commission_sellers_admin"
            if self.env.user.has_group("pba_goal_commision.group_goal_commission_admin")
            else "pba_goal_commision.action_goal_commission_sellers"
        )
        action = self.env["ir.actions.actions"]._for_xml_id(xmlid)
        period = self.env["goal.commission.period"]._get_default_period()
        return self.env["goal.commission.period"].action_with_period_context(action, period)
