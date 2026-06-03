from odoo import tools


class GoalCommissionReportMixin:
    _credit_notes_untaxed_sql = """
        COALESCE((
            SELECT SUM(ABS(cn.amount_untaxed))
            FROM account_move cn
            WHERE cn.reversed_entry_id = am.id
              AND cn.state = 'posted'
              AND cn.move_type = 'out_refund'
        ), 0)
    """

    @classmethod
    def _net_untaxed_sql(cls):
        return "GREATEST(0, am.amount_untaxed - (%s))" % cls._credit_notes_untaxed_sql

    @classmethod
    def _sql_rate_subquery(cls, currency_sql, company_sql, date_sql):
        """Tasa vigente en o antes de date_sql (fecha del documento, no la fecha actual)."""
        return """
            (
                SELECT r.rate
                FROM res_currency_rate r
                WHERE r.currency_id = (%(currency)s)
                  AND (r.company_id IS NULL OR r.company_id = (%(company)s))
                  AND r.name <= (%(date)s)::date
                ORDER BY r.company_id NULLS LAST, r.name DESC
                LIMIT 1
            )
        """ % {
            "currency": currency_sql,
            "company": company_sql,
            "date": date_sql,
        }

    @classmethod
    def _sql_convert_amount(cls, amount_sql, from_currency_sql, to_currency_sql, company_sql, date_sql):
        from_rate = cls._sql_rate_subquery(from_currency_sql, company_sql, date_sql)
        to_rate = cls._sql_rate_subquery(to_currency_sql, company_sql, date_sql)
        return """
            CASE
                WHEN (%(from)s) = (%(to)s) THEN (%(amount)s)
                ELSE (%(amount)s) * COALESCE(%(to_rate)s, 1.0) / NULLIF(COALESCE(%(from_rate)s, 1.0), 0)
            END
        """ % {
            "amount": amount_sql,
            "from": from_currency_sql,
            "to": to_currency_sql,
            "to_rate": to_rate,
            "from_rate": from_rate,
        }

    @classmethod
    def _invoice_base_where(cls):
        return """
            am.move_type = 'out_invoice'
            AND am.state = 'posted'
            AND am.invoice_user_id IS NOT NULL
            AND EXISTS (
                SELECT 1
                FROM res_users ru
                INNER JOIN goal_commission_tier gct ON gct.partner_id = ru.partner_id AND gct.active = TRUE
                WHERE ru.id = am.invoice_user_id
            )
            AND (
                rc.goal_commission_start_date IS NULL
                OR am.invoice_date >= rc.goal_commission_start_date
            )
            AND COALESCE(am.goal_commission_exception, FALSE) = FALSE
        """

    @classmethod
    def _drop_view(cls, env, table_name):
        tools.drop_view_if_exists(env.cr, table_name)
