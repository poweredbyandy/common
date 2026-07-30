from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression


class AccountAccount(models.Model):
    _inherit = "account.account"

    group_id = fields.Many2one(
        comodel_name="account.group",
        compute="_compute_account_group",
        search="_search_group_id",
        help="Account prefixes can determine account groups.",
    )
    group_label = fields.Char(
        string="Account Group",
        compute="_compute_group_label",
    )

    @api.depends(
        "group_id",
        "group_id.name",
        "group_id.code_prefix_start",
        "group_id.code_prefix_end",
    )
    def _compute_group_label(self):
        for account in self:
            if account.group_id:
                account.group_label = account.group_id.name
            else:
                account.group_label = _("Ungrouped")

    def action_open_create_account_group(self):
        self.ensure_one()
        if self.group_id:
            raise UserError(
                _(
                    "Account %(account)s already belongs to group %(group)s.",
                    account=self.display_name,
                    group=self.group_id.display_name,
                )
            )
        if not self.code:
            raise UserError(_("Set an account code before creating a group."))
        prefix = self._get_suggested_group_prefix()
        return {
            "name": _("Create Account Group"),
            "type": "ir.actions.act_window",
            "res_model": "account.account.create.group.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_account_id": self.id,
                "default_code_prefix_start": prefix,
                "default_code_prefix_end": prefix,
                "default_name": False,
                "active_id": self.id,
            },
        }

    def _get_suggested_group_prefix(self):
        self.ensure_one()
        code = self.code or ""
        if not code:
            return ""
        if len(code) == 1:
            return code

        company = self.env.company.root_id
        groups = self.env["account.group"].search([("company_id", "=", company.id)])
        lengths = [
            len(group.code_prefix_start)
            for group in groups
            if group.code_prefix_start and len(group.code_prefix_start) < len(code)
        ]
        if lengths:
            length = max(set(lengths), key=lengths.count)
            half_length = max(1, len(code) // 2)
            if half_length > length and (len(code) - length) >= 4:
                length = half_length
        else:
            length = max(1, len(code) // 2)

        length = max(1, min(length, len(code) - 1))
        return code[:length]

    @api.model
    def get_group_panel_data(self):
        company = self.env.company.root_id
        groups = self.env["account.group"].search(
            [("company_id", "=", company.id)],
            order="code_prefix_start, id",
        )
        items = []
        for group in groups:
            code = group.code_prefix_start or ""
            if (
                group.code_prefix_end
                and group.code_prefix_end != group.code_prefix_start
            ):
                code = "%s-%s" % (group.code_prefix_start, group.code_prefix_end)
            items.append(
                {
                    "type": "group",
                    "id": group.id,
                    "code": group.code_prefix_start or "",
                    "sort_code": group.code_prefix_start or "",
                    "label": "%s %s" % (code, group.name) if code else group.name,
                    "parent_id": group.parent_id.id or False,
                    "account_ids": [],
                    "sample_account_id": False,
                }
            )

        accounts = self.search([("code", "!=", False)], order="code, id")
        missing_groups = {}
        for account in accounts:
            if account.group_id:
                continue
            prefix = account._get_suggested_group_prefix()
            if not prefix:
                continue
            missing_groups.setdefault(
                prefix,
                {
                    "type": "missing_group",
                    "id": "prefix-%s" % prefix,
                    "code": prefix,
                    "sort_code": prefix,
                    "label": "%s %s" % (prefix, _("Ungrouped")),
                    "parent_id": False,
                    "account_ids": [],
                    "sample_account_id": account.id,
                },
            )
            missing_groups[prefix]["account_ids"].append(account.id)

        items.extend(missing_groups.values())
        items.sort(
            key=lambda item: (
                item["sort_code"],
                0 if item["type"] == "group" else 1,
                str(item["id"]),
            )
        )
        return {"items": items}

    def _search_group_id(self, operator, value):
        if operator in ("=", "!=") and not value:
            accounts = self.search([("code", "!=", False)])
            ungrouped_ids = accounts.filtered(lambda a: not a.group_id).ids
            if operator == "=":
                return [("id", "in", ungrouped_ids)]
            return [("id", "not in", ungrouped_ids)]

        if operator not in ("=", "in", "child_of"):
            raise UserError(_("Operation not supported"))

        Group = self.env["account.group"]
        if operator == "child_of":
            groups = Group.browse(
                value if isinstance(value, (list, tuple, set)) else [value]
            )
        elif operator == "in":
            groups = Group.browse(value)
        else:
            groups = Group.browse(
                value if isinstance(value, (list, tuple, set)) else [value]
            )
        groups = groups.exists()
        if not groups:
            return [("id", "=", False)]

        accounts = self.search([("code", "!=", False)])
        matching_ids = set()
        for group in groups:
            prefix_start = group.code_prefix_start
            prefix_end = group.code_prefix_end or prefix_start
            if not prefix_start:
                continue
            length = len(prefix_start)
            for account in accounts:
                code_prefix = (account.code or "")[:length]
                if len(code_prefix) < length:
                    continue
                if prefix_start <= code_prefix <= prefix_end:
                    matching_ids.add(account.id)
        return [("id", "in", list(matching_ids))]

    @api.model
    def _search_panel_domain_image(
        self, field_name, domain, set_count=False, limit=False
    ):
        if field_name != "group_id":
            return super()._search_panel_domain_image(
                field_name, domain, set_count=set_count, limit=limit
            )

        if expression.is_false(self, domain):
            return {}

        accounts = self.search(domain, limit=limit)
        domain_image = {}
        ungrouped_count = 0
        for account in accounts:
            group = account.group_id
            if not group:
                ungrouped_count += 1
                continue
            values = domain_image.get(group.id)
            if not values:
                values = {
                    "id": group.id,
                    "display_name": group.display_name,
                }
                if set_count:
                    values["__count"] = 0
                domain_image[group.id] = values
            if set_count:
                values["__count"] += 1

        if ungrouped_count:
            values = {
                "id": False,
                "display_name": _("Ungrouped"),
            }
            if set_count:
                values["__count"] = ungrouped_count
            domain_image[False] = values
        return domain_image

    @api.model
    def search_panel_select_range(self, field_name, **kwargs):
        result = super().search_panel_select_range(field_name, **kwargs)
        if field_name != "group_id" or result.get("error_msg"):
            return result

        search_domain = kwargs.get("search_domain", [])
        extra_domain = expression.AND(
            [
                kwargs.get("category_domain", []),
                kwargs.get("filter_domain", []),
            ]
        )
        ungrouped_domain = expression.AND(
            [search_domain, extra_domain, [("group_id", "=", False)]]
        )
        ungrouped_count = self.search_count(ungrouped_domain)
        if not ungrouped_count:
            return result

        values = result.get("values") or []
        if any(entry.get("id") is False for entry in values):
            for entry in values:
                if entry.get("id") is False:
                    entry["__count"] = ungrouped_count
                    entry["display_name"] = _("Ungrouped")
            return result

        ungrouped_values = {
            "id": False,
            "display_name": _("Ungrouped"),
        }
        parent_field = result.get("parent_field")
        if parent_field:
            ungrouped_values[parent_field] = False
        if kwargs.get("enable_counters"):
            ungrouped_values["__count"] = ungrouped_count
        values.append(ungrouped_values)
        result["values"] = values
        return result
