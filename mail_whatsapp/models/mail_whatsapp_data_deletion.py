import logging
import secrets
import string

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class MailWhatsappDataDeletion(models.Model):
    _name = "mail.whatsapp.data.deletion"
    _description = "Facebook Data Deletion Request"
    _order = "id desc"

    name = fields.Char(required=True, copy=False, default="New")
    confirmation_code = fields.Char(
        required=True,
        index=True,
        copy=False,
        readonly=True,
    )
    facebook_user_id = fields.Char(
        string="Facebook App-Scoped User ID",
        required=True,
        index=True,
        readonly=True,
    )
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("done", "Completed"),
            ("no_data", "No Data Found"),
        ],
        default="pending",
        required=True,
        copy=False,
    )
    status_message = fields.Text(readonly=True)
    status_url = fields.Char(compute="_compute_status_url")

    _sql_constraints = [
        (
            "confirmation_code_unique",
            "unique(confirmation_code)",
            "Confirmation code must be unique.",
        ),
    ]

    def _compute_status_url(self):
        base = self.get_base_url().rstrip("/")
        for record in self:
            record.status_url = (
                f"{base}/mail_whatsapp/facebook/data_deletion/"
                f"{record.confirmation_code}"
            )

    @api.model
    def _generate_confirmation_code(self):
        alphabet = string.ascii_uppercase + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(12))

    @api.model
    def create_from_facebook_user(self, facebook_user_id):
        code = self._generate_confirmation_code()
        record = self.sudo().create(
            {
                "name": _("Deletion %(code)s", code=code),
                "confirmation_code": code,
                "facebook_user_id": str(facebook_user_id),
                "state": "pending",
                "status_message": _(
                    "Your data deletion request was received and is being processed."
                ),
            }
        )
        record._process_deletion()
        return record

    def _process_deletion(self):
        """Delete or anonymize data linked to the Facebook app-scoped user id."""
        self.ensure_one()
        Account = self.env["mail.whatsapp.account"].sudo()
        accounts = Account.search(
            [("facebook_user_id", "=", self.facebook_user_id)]
        )
        deleted_accounts = len(accounts)
        if accounts:
            # Remove tokens and unlink Facebook identity; keep audit shell minimal.
            accounts.write(
                {
                    "token": False,
                    "app_secret": False,
                    "facebook_user_id": False,
                    "active": False,
                    "name": _("Deleted Facebook user %(uid)s", uid=self.facebook_user_id),
                }
            )
            _logger.info(
                "Processed Facebook data deletion for ASID %s on %s account(s)",
                self.facebook_user_id,
                deleted_accounts,
            )
            self.write(
                {
                    "state": "done",
                    "status_message": _(
                        "We deleted the WhatsApp account credentials linked to "
                        "your Facebook user in this application. "
                        "Accounts affected: %(count)s.",
                        count=deleted_accounts,
                    ),
                }
            )
        else:
            self.write(
                {
                    "state": "no_data",
                    "status_message": _(
                        "We did not find stored personal Facebook-linked data "
                        "for this user in the application. No further action was required."
                    ),
                }
            )
        return True
