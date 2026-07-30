from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountAccountCreateGroupWizard(models.TransientModel):
    _name = "account.account.create.group.wizard"
    _description = "Create Account Group from Account"

    account_id = fields.Many2one(
        comodel_name="account.account",
        string="Account",
        required=True,
        readonly=True,
    )
    account_code = fields.Char(related="account_id.code", string="Account Code")
    account_name = fields.Char(related="account_id.name", string="Account Name")
    name = fields.Char(
        string="Group Name",
        required=True,
        help="Name of the account group to create.",
    )
    code_prefix_start = fields.Char(string="Code Prefix From", required=True)
    code_prefix_end = fields.Char(string="Code Prefix To", required=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        account = self.env["account.account"].browse(
            self.env.context.get("default_account_id")
            or self.env.context.get("active_id")
        )
        if account:
            res["account_id"] = account.id
            suggested = account._get_suggested_group_prefix()
            if "code_prefix_start" not in res or not res.get("code_prefix_start"):
                res["code_prefix_start"] = suggested
            if "code_prefix_end" not in res or not res.get("code_prefix_end"):
                res["code_prefix_end"] = res.get("code_prefix_start") or suggested
            if "name" not in res:
                res["name"] = False
        return res

    def action_create_group(self):
        self.ensure_one()
        if not self.code_prefix_start or not self.code_prefix_end:
            raise UserError(_("Code prefixes are required."))
        if len(self.code_prefix_start) != len(self.code_prefix_end):
            raise UserError(
                _("The starting and ending code prefixes must have the same length.")
            )
        if self.code_prefix_start > self.code_prefix_end:
            raise UserError(
                _(
                    "The starting code prefix must be lower than or equal "
                    "to the ending one."
                )
            )

        company = self.env.company.root_id
        existing = self.env["account.group"].search(
            [
                ("company_id", "=", company.id),
                ("code_prefix_start", "=", self.code_prefix_start),
                ("code_prefix_end", "=", self.code_prefix_end),
            ],
            limit=1,
        )
        if existing:
            prefix = (
                self.code_prefix_start
                if self.code_prefix_start == self.code_prefix_end
                else "%s-%s" % (self.code_prefix_start, self.code_prefix_end)
            )
            raise UserError(
                _(
                    "An account group with prefix %(prefix)s already exists: %(group)s.",
                    prefix=prefix,
                    group=existing.display_name,
                )
            )

        group = self.env["account.group"].create(
            {
                "name": self.name,
                "code_prefix_start": self.code_prefix_start,
                "code_prefix_end": self.code_prefix_end,
                "company_id": company.id,
            }
        )
        accounts = self.env["account.account"].search([("code", "!=", False)])
        accounts.invalidate_recordset(["group_id", "group_label"])
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Account Group Created"),
                "message": _(
                    "Group %(group)s was created and linked to matching accounts.",
                    group=group.display_name,
                ),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.client", "tag": "soft_reload"},
            },
        }
