import re

from odoo import api, models
from odoo.osv import expression


class Base(models.AbstractModel):
    _inherit = "base"

    @api.model
    def _wildcard_to_sql_pattern(self, value):
        parts = value.split("*")
        escaped_parts = [re.sub(r"([_%\\])", r"\\\1", part) for part in parts]
        return "%" + "%".join(escaped_parts) + "%"

    @api.model
    def _wildcard_preprocess_domain(self, domain):
        if not domain:
            return domain
        result = []
        for item in domain:
            if isinstance(item, (list, tuple)) and len(item) == 3:
                left, operator, value = item
                if (
                    isinstance(value, str)
                    and "*" in value
                    and operator in expression.WILDCARD_OPERATORS
                ):
                    value = self._wildcard_to_sql_pattern(value)
                result.append((left, operator, value))
            else:
                result.append(item)
        return result

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        domain = self._wildcard_preprocess_domain(domain)
        return super()._search(domain, offset=offset, limit=limit, order=order)

    @api.model
    def _condition_to_sql(self, alias, fname, operator, value, query):
        if (
            isinstance(value, str)
            and "*" in value
            and operator in expression.WILDCARD_OPERATORS
        ):
            value = self._wildcard_to_sql_pattern(value)
        return super()._condition_to_sql(alias, fname, operator, value, query)
