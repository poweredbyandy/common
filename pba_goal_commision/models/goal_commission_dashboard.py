from odoo import api, fields, models


class GoalCommissionDashboardMixin(models.AbstractModel):
    _name = "goal.commission.dashboard.mixin"
    _description = "Utilidades de rendimiento para dashboard de comisiones"

    @api.model
    def _goal_commission_batch_credit_untaxed(self, invoice_ids):
        if not invoice_ids:
            return {}
        self.env["account.move"].flush_model(["amount_untaxed", "reversed_entry_id", "state", "move_type"])
        self.env.cr.execute(
            """
            SELECT reversed_entry_id, COALESCE(SUM(ABS(amount_untaxed)), 0)
            FROM account_move
            WHERE reversed_entry_id = ANY(%s)
              AND state = 'posted'
              AND move_type = 'out_refund'
            GROUP BY reversed_entry_id
            """,
            [list(invoice_ids)],
        )
        return dict(self.env.cr.fetchall())

    @api.model
    def _goal_commission_invoice_eligible_for_progress(self, invoice, invoice_date):
        if invoice.goal_commission_exception:
            return False
        if invoice.payment_state == "reversed":
            return False
        start_date = invoice.company_id.goal_commission_start_date
        if start_date and invoice_date and invoice_date < start_date:
            return False
        seller = invoice.invoice_user_id.partner_id
        if not seller or not seller.goal_commission_tier_ids.filtered("active"):
            return False
        return True

    @api.model
    def _goal_commission_invoice_progress_domain(self, user_ids, period, start_date):
        domain = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("invoice_user_id", "in", user_ids),
            ("payment_state", "!=", "reversed"),
        ]
        if period:
            domain.extend([
                ("invoice_date", ">=", period.date_start),
                ("invoice_date", "<=", period.date_end),
            ])
        elif start_date:
            domain.append(("invoice_date", ">=", start_date))
        return domain

    @api.model
    def _goal_commission_net_untaxed_map(self, invoices):
        credit_map = self._goal_commission_batch_credit_untaxed(invoices.ids)
        result = {}
        for invoice in invoices:
            credit = credit_map.get(invoice.id, 0.0)
            result[invoice.id] = max(0.0, invoice.amount_untaxed - credit)
        return result

    @api.model
    def _goal_commission_reset_progress_fields(self, partners):
        for partner in partners:
            partner.goal_invoice_amount = 0.0
            partner.goal_collected_amount = 0.0
            partner.goal_commission_target_amount = 0.0
            partner.goal_invoice_progress_pct = 0.0
            partner.goal_invoice_progress_display = "0.00"
            partner.goal_collection_progress_pct = 0.0
            partner.goal_collection_progress_display = "0.00"
            partner.goal_collected_target_progress_pct = 0.0
            partner.goal_collected_target_progress_display = "0.00"
            partner.goal_commission_current_percent = 0.0
            partner.goal_commission_current_tier_name = ""
            partner.goal_commission_current_tier_target = 0.0
            partner.goal_invoice_tier_progress_pct = 0.0
            partner.goal_invoice_tier_progress_display = "0.00"
            partner.goal_tier_achievement_display = "—"
            partner.goal_tier_badges_html = ""
            partner.goal_achieved_tier_count = 0

    @api.model
    def _goal_commission_apply_progress_totals(self, partners, totals_by_partner):
        for partner in partners:
            totals = totals_by_partner.get(partner.id)
            if not totals:
                continue
            currency = partner.goal_commission_currency_id or totals["currency"]
            invoiced = currency.round(totals["invoiced"])
            collected = currency.round(totals["collected"])
            partner.goal_invoice_amount = invoiced
            partner.goal_collected_amount = collected
            status_list = partner._get_goal_tier_status_list(invoiced)
            current_rows = [row for row in status_list if row["state"] == "current"]
            current_row = current_rows[0] if current_rows else {}
            current_tier = current_row.get("tier") or partner.env["goal.commission.tier"]
            tier_progress_pct = current_row.get("progress_pct", 0.0)
            tier_target = current_row.get("max_amount") or partner._get_goal_target_for_amount(invoiced)
            if current_tier and not current_tier.max_amount:
                tier_target = invoiced if invoiced else current_tier.min_amount
            partner.goal_commission_current_tier_name = current_tier.name if current_tier else ""
            partner.goal_commission_current_tier_target = currency.round(tier_target or 0.0)
            partner.goal_commission_target_amount = partner.goal_commission_current_tier_target
            partner.goal_invoice_tier_progress_pct = tier_progress_pct
            partner.goal_invoice_tier_progress_display = "{:.2f}".format(tier_progress_pct or 0.0)
            partner.goal_invoice_progress_pct = tier_progress_pct
            partner.goal_invoice_progress_display = partner.goal_invoice_tier_progress_display
            target = partner.goal_commission_current_tier_target or 0.0
            partner.goal_collection_progress_pct = (
                min(100.0, (collected / invoiced) * 100.0) if invoiced else 0.0
            )
            partner.goal_collected_target_progress_pct = (
                min(100.0, (collected / target) * 100.0) if target else 0.0
            )
            partner.goal_collection_progress_display = "{:.2f}".format(
                partner.goal_collection_progress_pct or 0.0
            )
            partner.goal_collected_target_progress_display = "{:.2f}".format(
                partner.goal_collected_target_progress_pct or 0.0
            )
            partner.goal_commission_current_percent = partner._get_goal_commission_percent_for_amount(invoiced)
            partner.goal_achieved_tier_count = len([row for row in status_list if row["state"] == "achieved"])
            partner.goal_tier_achievement_display = partner._format_goal_tier_achievement_display(status_list)
            partner.goal_tier_badges_html = partner._format_goal_tier_badges_html(status_list)
