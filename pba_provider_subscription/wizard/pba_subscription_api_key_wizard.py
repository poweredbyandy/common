from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PbaSubscriptionApiKeyWizard(models.TransientModel):
    _name = "pba.subscription.api.key.wizard"
    _description = "Generate Client Subscription API Key"

    partner_id = fields.Many2one(
        "res.partner",
        string="Empresa cliente",
        required=True,
        domain="[('is_company', '=', True)]",
    )
    user_id = fields.Many2one(
        "res.users",
        string="Usuario portal",
        domain="[('share', '=', True), ('active', '=', True)]",
    )
    user_login = fields.Char(related="user_id.login", string="Usuario", readonly=True)
    key_name = fields.Char(
        string="Descripción de la clave",
        required=True,
        default="Customer Subscription",
    )
    duration = fields.Selection(
        [
            ("0", "Persistente"),
            ("365", "1 año"),
            ("180", "6 meses"),
            ("90", "3 meses"),
        ],
        string="Duración",
        required=True,
        default="0",
    )
    existing_key_ids = fields.One2many(
        related="user_id.api_key_ids",
        string="API Keys existentes",
        readonly=True,
    )
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("done", "Hecho"),
        ],
        default="draft",
        required=True,
    )
    generated_key = fields.Char(string="API Key", readonly=True)
    create_portal_user = fields.Boolean(
        string="Crear usuario portal si no existe",
        default=False,
    )
    new_user_name = fields.Char(string="Nombre del usuario")
    new_user_login = fields.Char(string="Login del usuario")
    new_user_email = fields.Char(string="Email del usuario")

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        self.user_id = False
        if not self.partner_id:
            return
        users = self._pba_find_portal_users(self.partner_id)
        if len(users) == 1:
            self.user_id = users
        elif not users:
            self.create_portal_user = True
            self.new_user_name = self.partner_id.name
            self.new_user_login = self.partner_id.email or ""
            self.new_user_email = self.partner_id.email or ""

    @api.model
    def _pba_find_portal_users(self, partner):
        commercial = partner.commercial_partner_id
        return self.env["res.users"].search(
            [
                ("share", "=", True),
                ("active", "=", True),
                ("partner_id", "child_of", commercial.id),
            ]
        )

    @api.onchange("user_id")
    def _onchange_user_id(self):
        if self.user_id:
            self.create_portal_user = False

    def _pba_get_expiration_date(self):
        self.ensure_one()
        days = int(self.duration)
        if days <= 0:
            return False
        return fields.Datetime.now() + relativedelta(days=days)

    def _pba_ensure_portal_user(self):
        self.ensure_one()
        if self.user_id:
            return self.user_id
        if not self.create_portal_user:
            raise UserError(
                _("Select a portal user or enable creating a new portal user.")
            )
        if not self.new_user_login:
            raise UserError(_("Login is required to create the portal user."))
        partner = self.partner_id.commercial_partner_id
        contact = self.env["res.partner"].create(
            {
                "name": self.new_user_name or partner.name,
                "email": self.new_user_email or self.new_user_login,
                "parent_id": partner.id,
                "type": "contact",
            }
        )
        group_portal = self.env.ref("base.group_portal")
        user = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": self.new_user_name or partner.name,
                "login": self.new_user_login,
                "email": self.new_user_email or self.new_user_login,
                "partner_id": contact.id,
                "groups_id": [(6, 0, [group_portal.id])],
            }
        )
        self.user_id = user
        return user

    def action_generate_key(self):
        self.ensure_one()
        user = self._pba_ensure_portal_user()
        if not user.share:
            raise UserError(_("The selected user must be a portal user."))
        key = self.env["res.users.apikeys"]._pba_generate_for_user(
            user,
            self.key_name,
            self._pba_get_expiration_date(),
        )
        self.write(
            {
                "generated_key": key,
                "state": "done",
                "user_id": user.id,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
