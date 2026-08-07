from urllib.parse import urlparse

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MailWhatsappTemplateButton(models.Model):
    _name = "mail.whatsapp.template.button"
    _description = "WhatsApp Template Button"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    name = fields.Char(string="Button Text", size=25, required=True)
    wa_template_id = fields.Many2one(
        "mail.whatsapp.template",
        required=True,
        ondelete="cascade",
        index=True,
    )
    button_type = fields.Selection(
        [("url", "Visit Website")],
        string="Type",
        required=True,
        default="url",
    )
    url_type = fields.Selection(
        [
            ("static", "Static"),
            ("dynamic", "Dynamic"),
        ],
        string="URL Type",
        default="dynamic",
        required=True,
    )
    website_url = fields.Char(
        string="Website URL",
        help="Base URL registered in Meta. For dynamic buttons use a trailing "
        "slash, e.g. https://your-company.com/",
    )
    demo_value = fields.Char(
        string="Example Dynamic Path",
        default="my/orders/1?access_token=demo",
        help="Example suffix sent to Meta when submitting a dynamic URL button.",
    )

    _sql_constraints = [
        (
            "unique_name_button_template",
            "unique(name, wa_template_id)",
            "Button names must be unique per template.",
        ),
    ]

    @api.onchange("website_url")
    def _onchange_website_url(self):
        if self.website_url:
            parsed = urlparse(self.website_url)
            if not (parsed.scheme in {"http", "https"} and parsed.netloc):
                self.website_url = "https://%s" % self.website_url

    @api.constrains("button_type", "url_type", "website_url")
    def _check_website_url(self):
        for button in self:
            if button.button_type != "url":
                continue
            if not button.website_url:
                raise ValidationError(
                    _("Please set a website URL for button %(name)s.")
                    % {"name": button.name}
                )
            parsed = urlparse(button.website_url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValidationError(
                    _("The website URL for button %(name)s is invalid.")
                    % {"name": button.name}
                )

    def _get_meta_button_data(self):
        self.ensure_one()
        data = {
            "type": "URL",
            "text": self.name,
            "url": self.website_url or "",
        }
        if self.url_type == "dynamic":
            base = self.website_url or ""
            if not base.endswith("/"):
                base = "%s/" % base.rstrip("/")
            data["url"] = "%s{{1}}" % base
            example = (self.demo_value or "preview").lstrip("/")
            data["example"] = "%s%s" % (base, example)
        return data

    def _resolve_dynamic_suffix(self, record):
        """Return the dynamic URL suffix (without leading slash) for Meta send."""
        self.ensure_one()
        if self.url_type != "dynamic":
            return ""
        full_url = False
        if record and hasattr(record, "_whatsapp_template_button_url"):
            full_url = record._whatsapp_template_button_url(self)
        elif record and hasattr(record, "get_portal_url"):
            full_url = "%s%s" % (
                record.get_base_url().rstrip("/"),
                record.get_portal_url(),
            )
        if not full_url:
            return (self.demo_value or "preview").lstrip("/")
        base = (self.website_url or "").rstrip("/")
        if full_url.startswith(base):
            return full_url[len(base) :].lstrip("/")
        if "://" in full_url:
            parsed = urlparse(full_url)
            return ("%s?%s" % (parsed.path, parsed.query)).lstrip("/").rstrip("?")
        return full_url.lstrip("/")

    def _resolve_full_url(self, record=None):
        """Return the absolute URL shown/opened for this button."""
        self.ensure_one()
        if self.button_type != "url":
            return False
        if self.url_type == "static":
            return self.website_url or False
        suffix = self._resolve_dynamic_suffix(record)
        base = (self.website_url or "").rstrip("/")
        if not base:
            return False
        if not suffix:
            return "%s/" % base
        return "%s/%s" % (base, suffix.lstrip("/"))
