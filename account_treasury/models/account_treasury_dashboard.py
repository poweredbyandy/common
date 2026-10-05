from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools import SQL

BUCKET_KEYS = (
    "planned_in",
    "planned_out",
    "real_in",
    "real_out",
    "pending_in",
    "pending_out",
)


class AccountTreasuryDashboard(models.AbstractModel):
    _name = "account.treasury.dashboard"
    _description = "Treasury Dashboard"

    @api.model
    def get_dashboard_data(
        self,
        date_from,
        date_to,
        currency_id=False,
        rate_mode="document",
        group_by="day",
    ):
        self.env["account.treasury.forecast"].check_access("read")
        self.env["account.treasury.match"].check_access("read")
        date_from = fields.Date.to_date(date_from)
        date_to = fields.Date.to_date(date_to)
        currency = (
            self.env["res.currency"].browse(currency_id).exists()
            or self.env.company.currency_id
        )
        rows = self._fetch_rows(date_from, date_to, currency, rate_mode)
        buckets = self._init_buckets(date_from, date_to, group_by)
        items = defaultdict(list)
        for row in rows:
            amount = currency.round(row["amount"] * row["rate"])
            residual = currency.round(row["residual"] * row["rate"])
            suffix = "in" if row["flow_type"] == "inflow" else "out"
            bucket = buckets[self._bucket_key(row["date"], group_by)]
            if row["kind"] == "forecast":
                bucket[f"planned_{suffix}"] += amount
                bucket[f"pending_{suffix}"] += residual
            else:
                bucket[f"real_{suffix}"] += amount
            if group_by == "day":
                items[fields.Date.to_string(row["date"])].append(
                    {
                        "kind": row["kind"],
                        "forecast_id": row["forecast_id"],
                        "match_id": row["match_id"],
                        "name": row["name"],
                        "partner": row["partner_name"] or "",
                        "category": row["category_name"] or "",
                        "color": row["category_color"] or 0,
                        "flow_type": row["flow_type"],
                        "state": row["state"],
                        "reference": row["reference"] or "",
                        "amount": amount,
                        "residual": residual,
                    }
                )
        return {
            "currency_id": currency.id,
            "currencies": self.env["res.currency"].search_read(
                [], ["name", "symbol"], order="name"
            ),
            "buckets": self._finalize_buckets(buckets, currency),
            "items": items,
            "totals": self._compute_totals(buckets, currency),
            "today": fields.Date.to_string(fields.Date.context_today(self)),
        }

    @api.model
    def _fetch_rows(self, date_from, date_to, currency, rate_mode):
        for model in ("account.treasury.forecast", "account.treasury.match", "res.currency.rate"):
            self.env[model].flush_model()
        company_ids = tuple(self.env.companies.ids)
        conversion_date = SQL(
            "%s::date", fields.Date.context_today(self)
        ) if rate_mode == "today" else SQL("movement.date")
        query = SQL(
            """
            WITH movement AS (
                SELECT 'forecast' AS kind,
                       forecast.id AS forecast_id,
                       NULL::integer AS match_id,
                       forecast.date,
                       forecast.flow_type,
                       forecast.state,
                       forecast.amount,
                       forecast.amount_residual AS residual,
                       forecast.currency_id,
                       forecast.company_id,
                       forecast.name,
                       forecast.partner_id,
                       forecast.category_id,
                       NULL::varchar AS reference
                  FROM account_treasury_forecast forecast
                 WHERE forecast.company_id IN %(company_ids)s
                   AND forecast.state != 'cancel'
                   AND forecast.date BETWEEN %(date_from)s AND %(date_to)s
                 UNION ALL
                SELECT 'real' AS kind,
                       forecast.id,
                       treasury_match.id,
                       treasury_match.date,
                       forecast.flow_type,
                       forecast.state,
                       treasury_match.real_amount,
                       0.0,
                       treasury_match.real_currency_id,
                       forecast.company_id,
                       forecast.name,
                       COALESCE(treasury_match.partner_id, forecast.partner_id),
                       forecast.category_id,
                       treasury_match.reference
                  FROM account_treasury_match treasury_match
                  JOIN account_treasury_forecast forecast
                    ON forecast.id = treasury_match.forecast_id
                 WHERE forecast.company_id IN %(company_ids)s
                   AND treasury_match.date BETWEEN %(date_from)s AND %(date_to)s
            )
            SELECT movement.*,
                   partner.name AS partner_name,
                   category.name AS category_name,
                   category.color AS category_color,
                   COALESCE(target_rate.rate, 1.0)
                       / COALESCE(NULLIF(source_rate.rate, 0.0), 1.0) AS rate
              FROM movement
              JOIN res_company company ON company.id = movement.company_id
         LEFT JOIN res_partner partner ON partner.id = movement.partner_id
         LEFT JOIN account_treasury_category category
                ON category.id = movement.category_id
         LEFT JOIN LATERAL (%(source_rate)s) source_rate ON TRUE
         LEFT JOIN LATERAL (%(target_rate)s) target_rate ON TRUE
          ORDER BY movement.date, movement.kind, movement.forecast_id
            """,
            company_ids=company_ids,
            date_from=date_from,
            date_to=date_to,
            source_rate=self._rate_query(SQL("movement.currency_id"), conversion_date),
            target_rate=self._rate_query(SQL("%s", currency.id), conversion_date),
        )
        return self.env.execute_query_dict(query)

    @api.model
    def _rate_query(self, currency_sql, conversion_date):
        return SQL(
            """
            SELECT rate.rate
              FROM res_currency_rate rate
             WHERE rate.currency_id = %(currency)s
               AND (
                    rate.company_id IS NULL
                    OR rate.company_id = split_part(company.parent_path, '/', 1)::integer
               )
          ORDER BY (rate.name <= %(conversion_date)s) DESC,
                   rate.company_id,
                   CASE WHEN rate.name <= %(conversion_date)s THEN rate.name END DESC,
                   rate.name
             LIMIT 1
            """,
            currency=currency_sql,
            conversion_date=conversion_date,
        )

    @api.model
    def _bucket_key(self, value, group_by):
        if group_by == "month":
            return value.strftime("%Y-%m")
        return fields.Date.to_string(value)

    @api.model
    def _init_buckets(self, date_from, date_to, group_by):
        step = relativedelta(months=1) if group_by == "month" else relativedelta(days=1)
        buckets = {}
        cursor = date_from.replace(day=1) if group_by == "month" else date_from
        while cursor <= date_to:
            buckets[self._bucket_key(cursor, group_by)] = dict.fromkeys(
                BUCKET_KEYS, 0.0
            )
            cursor += step
        return buckets

    @api.model
    def _finalize_buckets(self, buckets, currency):
        balance = 0.0
        result = []
        for key, values in buckets.items():
            balance += (
                values["real_in"]
                - values["real_out"]
                + values["pending_in"]
                - values["pending_out"]
            )
            result.append(
                {
                    "key": key,
                    **{name: currency.round(value) for name, value in values.items()},
                    "balance": currency.round(balance),
                }
            )
        return result

    @api.model
    def _compute_totals(self, buckets, currency):
        totals = dict.fromkeys(BUCKET_KEYS, 0.0)
        for values in buckets.values():
            for name in BUCKET_KEYS:
                totals[name] += values[name]
        totals["net"] = (
            totals["real_in"]
            - totals["real_out"]
            + totals["pending_in"]
            - totals["pending_out"]
        )
        return {name: currency.round(value) for name, value in totals.items()}
