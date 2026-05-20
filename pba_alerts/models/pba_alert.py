from dateutil.relativedelta import relativedelta

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError

EVENT_TYPES_WITH_DELAY = {
    "draft_invoice_old",
    "quotation_no_followup",
}


class PbaAlert(models.Model):
    _name = "pba.alert"
    _description = "Configuración de alerta PBA"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    event_type = fields.Selection(
        selection=[
            ("overdue_invoice", "Facturas vencidas"),
            ("created_invoice", "Facturas creadas"),
            ("credit_note", "Notas de crédito"),
            ("return_picking", "Devoluciones"),
            ("draft_invoice_old", "Facturas en borrador antiguas"),
            ("sale_confirmed_not_invoiced", "Pedido confirmado sin facturar"),
            ("quotation_no_followup", "Cotización sin seguimiento"),
            ("return_without_credit_note", "Devolución sin nota de crédito"),
            ("sale_delivered_not_invoiced", "Pedido entregado sin facturar"),
        ],
        required=True,
    )
    delay_days = fields.Integer(
        string="Días de antigüedad",
        default=7,
        help="Documentos con más días sin cambios o sin seguimiento entran en la alerta.",
    )
    user_ids = fields.Many2many(
        "res.users",
        "pba_alert_res_users_rel",
        "alert_id",
        "user_id",
        string="Notificar a",
    )
    activity_type_id = fields.Many2one(
        "mail.activity.type",
        string="Tipo de actividad",
    )
    summary = fields.Char(translate=True)
    note = fields.Html(translate=True, sanitize_style=True)
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        default=lambda self: self.env.company,
    )
    schedule_enabled = fields.Boolean(
        string="Ejecución programada",
        default=True,
        help="Si está activo, se revisan documentos según el intervalo configurado.",
    )
    interval_number = fields.Integer(
        string="Cada",
        default=1,
        required=True,
    )
    interval_type = fields.Selection(
        selection=[
            ("minutes", "Minutos"),
            ("hours", "Horas"),
            ("days", "Días"),
            ("weeks", "Semanas"),
            ("months", "Meses"),
        ],
        string="Unidad",
        default="days",
        required=True,
    )
    schedule_label = fields.Char(
        string="Frecuencia",
        compute="_compute_schedule_label",
    )
    last_run = fields.Datetime(string="Última ejecución", readonly=True)
    cron_id = fields.Many2one(
        "ir.cron",
        string="Tarea programada",
        copy=False,
        readonly=True,
        ondelete="set null",
    )

    _sql_constraints = [
        (
            "pba_alert_interval_number_positive",
            "CHECK(interval_number > 0)",
            "El intervalo debe ser mayor que cero.",
        ),
        (
            "pba_alert_delay_days_positive",
            "CHECK(delay_days > 0)",
            "Los días de antigüedad deben ser mayor que cero.",
        ),
    ]

    @api.depends("interval_number", "interval_type", "schedule_enabled")
    def _compute_schedule_label(self):
        unit_labels = dict(self._fields["interval_type"].selection)
        for alert in self:
            if not alert.schedule_enabled:
                alert.schedule_label = _("Desactivada")
                continue
            unit = unit_labels.get(alert.interval_type, "")
            alert.schedule_label = _("%(number)s %(unit)s", number=alert.interval_number, unit=unit)

    def _activity_summary(self):
        self.ensure_one()
        return self.summary or self.name

    def _activity_type(self):
        self.ensure_one()
        return self.activity_type_id or self.env.ref(
            "mail.mail_activity_data_todo", raise_if_not_found=False
        )

    def _filter_records_by_company(self, records):
        self.ensure_one()
        if not self.company_id:
            return records
        return records.filtered(lambda r: r.company_id == self.company_id)

    def _has_pending_activity(self, record, user, summary):
        return bool(
            self.env["mail.activity"].search_count(
                [
                    ("res_model", "=", record._name),
                    ("res_id", "=", record.id),
                    ("user_id", "=", user.id),
                    ("summary", "=", summary),
                ],
                limit=1,
            )
        )

    def _get_delay_limit_datetime(self):
        self.ensure_one()
        return fields.Datetime.now() - relativedelta(days=self.delay_days)

    def _get_overdue_invoices(self):
        today = fields.Date.context_today(self)
        return self.env["account.move"].search(
            [
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("payment_state", "in", ("not_paid", "partial", "in_payment")),
                ("invoice_date_due", "<", today),
            ]
        )

    def _get_old_draft_invoices(self):
        limit_dt = self._get_delay_limit_datetime()
        return self.env["account.move"].search(
            [
                ("move_type", "=", "out_invoice"),
                ("state", "=", "draft"),
                ("create_date", "<=", limit_dt),
            ]
        )

    def _get_sale_confirmed_not_invoiced(self):
        return self.env["sale.order"].search(
            [
                ("state", "=", "sale"),
                ("invoice_status", "in", ("to invoice", "no")),
            ]
        )

    def _get_quotations_without_followup(self):
        limit_dt = self._get_delay_limit_datetime()
        return self.env["sale.order"].search(
            [
                ("state", "in", ("draft", "sent")),
                ("write_date", "<=", limit_dt),
            ]
        )

    def _get_sale_delivered_not_invoiced(self):
        return self.env["sale.order"].search(
            [
                ("state", "=", "sale"),
                ("delivery_status", "=", "full"),
                ("invoice_status", "in", ("to invoice", "no")),
            ]
        )

    def _get_returns_without_credit_note(self):
        returns = self.env["stock.picking"].search(
            [
                ("return_id", "!=", False),
                ("state", "=", "done"),
            ]
        )
        result = self.env["stock.picking"]
        for picking in returns:
            sale = picking.sale_id or picking.return_id.sale_id
            if not sale:
                continue
            has_refund = sale.invoice_ids.filtered(
                lambda move: move.move_type == "out_refund" and move.state == "posted"
            )
            if not has_refund:
                result |= picking
        return result

    def _get_target_records(self):
        self.ensure_one()
        if self.event_type == "overdue_invoice":
            return self._get_overdue_invoices()
        if self.event_type == "created_invoice":
            return self.env["account.move"].search(
                [
                    ("move_type", "=", "out_invoice"),
                    ("state", "=", "posted"),
                ]
            )
        if self.event_type == "credit_note":
            return self.env["account.move"].search(
                [
                    ("move_type", "in", ("out_refund", "in_refund")),
                    ("state", "=", "posted"),
                ]
            )
        if self.event_type == "return_picking":
            return self.env["stock.picking"].search(
                [
                    ("return_id", "!=", False),
                    ("state", "=", "done"),
                ]
            )
        if self.event_type == "draft_invoice_old":
            return self._get_old_draft_invoices()
        if self.event_type == "sale_confirmed_not_invoiced":
            return self._get_sale_confirmed_not_invoiced()
        if self.event_type == "quotation_no_followup":
            return self._get_quotations_without_followup()
        if self.event_type == "return_without_credit_note":
            return self._get_returns_without_credit_note()
        if self.event_type == "sale_delivered_not_invoiced":
            return self._get_sale_delivered_not_invoiced()
        return self.env["pba.alert"].browse()

    def _should_have_cron(self):
        self.ensure_one()
        return self.active and self.schedule_enabled and self.user_ids

    def _prepare_cron_vals(self):
        self.ensure_one()
        return {
            "name": _("PBA Alerta: %s", self.name),
            "model_id": self.env["ir.model"]._get("pba.alert").id,
            "state": "code",
            "code": f"model.browse({self.id})._cron_execute()",
            "interval_number": self.interval_number,
            "interval_type": self.interval_type,
            "active": self._should_have_cron(),
            "user_id": SUPERUSER_ID,
        }

    def _sync_cron(self):
        Cron = self.env["ir.cron"].sudo()
        for alert in self:
            if alert.cron_id:
                alert.cron_id.write(alert._prepare_cron_vals())
            elif alert._should_have_cron():
                cron = Cron.create(alert._prepare_cron_vals())
                alert.with_context(pba_alerts_skip_cron_sync=True).write({"cron_id": cron.id})

    def _unlink_cron(self):
        crons = self.cron_id.sudo()
        self.with_context(pba_alerts_skip_cron_sync=True).write({"cron_id": False})
        crons.unlink()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_cron()
        return records

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get("pba_alerts_skip_cron_sync"):
            return res
        if set(vals) & {
            "active",
            "schedule_enabled",
            "interval_number",
            "interval_type",
            "name",
            "user_ids",
        }:
            to_disable = self.filtered(
                lambda a: not a.active or not a.schedule_enabled or not a.user_ids
            )
            to_sync = self - to_disable
            if to_disable:
                for alert in to_disable:
                    if alert.cron_id:
                        alert.cron_id.sudo().write({"active": False})
            to_sync._sync_cron()
        return res

    def unlink(self):
        crons = self.cron_id.sudo()
        res = super().unlink()
        crons.unlink()
        return res

    def schedule_activities(self, records):
        created = 0
        for alert in self:
            records = alert._filter_records_by_company(records)
            if not alert.user_ids or not records:
                continue
            activity_type = alert._activity_type()
            if not activity_type:
                continue
            summary = alert._activity_summary()
            for record in records:
                for user in alert.user_ids:
                    if alert._has_pending_activity(record, user, summary):
                        continue
                    record.activity_schedule(
                        activity_type_id=activity_type.id,
                        user_id=user.id,
                        summary=summary,
                        note=alert.note or "",
                    )
                    created += 1
        return created

    def _cron_execute(self):
        for alert in self:
            if not alert.active or not alert.user_ids:
                continue
            alert.schedule_activities(alert._get_target_records())
            alert.with_context(pba_alerts_skip_cron_sync=True).write(
                {"last_run": fields.Datetime.now()}
            )

    def action_generate_alerts(self):
        alerts = self.filtered("active")
        if not alerts:
            raise UserError(_("No hay alertas activas para procesar."))
        for alert in alerts:
            if not alert.user_ids:
                raise UserError(
                    _('Asigne al menos un usuario en la alerta "%s".') % alert.name
                )
        total = sum(alert.schedule_activities(alert._get_target_records()) for alert in alerts)
        alerts.with_context(pba_alerts_skip_cron_sync=True).write(
            {"last_run": fields.Datetime.now()}
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Alertas generadas"),
                "message": _("%s actividad(es) creada(s).", total),
                "type": "success",
                "sticky": False,
            },
        }

    @api.model
    def _register_hook(self):
        super()._register_hook()
        self._remove_legacy_cron()
        self.search(
            [
                ("cron_id", "=", False),
                ("schedule_enabled", "=", True),
                ("active", "=", True),
            ]
        )._sync_cron()

    @api.model
    def _remove_legacy_cron(self):
        legacy = self.env.ref(
            "pba_alerts.ir_cron_pba_alert_overdue_invoices",
            raise_if_not_found=False,
        )
        if legacy:
            legacy.unlink()
