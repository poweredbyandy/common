import logging
import re

from odoo import Command, _, api, exceptions, fields, models
from odoo.exceptions import ValidationError
from odoo.addons.phone_validation.tools import phone_validation
from odoo.addons.mail_whatsapp.tools import phone_validation as phone_validation_wa

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    wa_channel_count = fields.Integer(
        string="WhatsApp Channel Count",
        compute="_compute_wa_channel_count",
    )

    @api.constrains("mobile")
    def _check_unique_mobile_number(self):
        """Prevent two contacts from sharing the same mobile number."""
        for partner in self:
            digits = partner._get_mobile_digits()
            if not digits:
                continue
            duplicates = partner._find_partners_with_mobile_digits(digits)
            if duplicates:
                raise ValidationError(
                    _(
                        "Another contact already uses the mobile number "
                        "%(mobile)s (%(name)s).",
                        mobile=partner.mobile,
                        name=duplicates[0].display_name,
                    )
                )

    def _compute_wa_channel_count(self):
        partner_channel_counts = {partner.id: 0 for partner in self}
        member_count_by_partner = self.env["discuss.channel.member"]._read_group(
            domain=[
                ("channel_id.channel_type", "=", "whatsapp"),
                ("partner_id", "in", self.ids),
            ],
            groupby=["partner_id"],
            aggregates=["id:count"],
        )
        for partner, count in member_count_by_partner:
            partner_channel_counts[partner.id] += count
        for partner in self:
            partner.wa_channel_count = partner_channel_counts[partner.id]

    def write(self, vals):
        res = super().write(vals)
        if "name" in vals:
            self._sync_whatsapp_channel_names()
        return res

    def _sync_whatsapp_channel_names(self):
        """Keep WhatsApp Discuss channel titles aligned with the contact name."""
        Channel = self.env["discuss.channel"].sudo()
        channels = Channel.search(
            [
                ("channel_type", "=", "whatsapp"),
                ("whatsapp_partner_id", "in", self.ids),
            ]
        )
        for channel in channels:
            partner_name = channel.whatsapp_partner_id.name
            if partner_name and channel.name != partner_name:
                channel.write({"name": partner_name})
                channel._bus_send_store(channel, {"name": channel.name})

    def _get_mobile_digits(self):
        """Return digits-only mobile, preferring E164 when formatting works."""
        self.ensure_one()
        if not self.mobile:
            return ""
        formatted_number, _country, _national, _code = self._parse_whatsapp_number(
            self.mobile
        )
        source = formatted_number or self.mobile
        return re.sub(r"\D", "", source or "")

    def _find_partners_with_mobile_digits(self, digits):
        """Return other partners whose mobile matches the given digits."""
        self.ensure_one()
        digits = re.sub(r"\D", "", digits or "")
        if not digits:
            return self.browse()
        query = """
            SELECT partner.id
            FROM res_partner partner
            WHERE partner.mobile IS NOT NULL
              AND partner.id != %s
              AND REGEXP_REPLACE(partner.mobile, '[^0-9]', '', 'g') = %s
            ORDER BY partner.id
            LIMIT 1
        """
        self.env.cr.execute(query, (self.id or 0, digits))
        return self.browse([row[0] for row in self.env.cr.fetchall()])

    def _parse_whatsapp_number(self, number):
        search_number = number if number.startswith("+") else f"+{number}"
        try:
            formatted_number = phone_validation_wa.wa_phone_format(
                self.env.company,
                number=search_number,
                force_format="E164",
                raise_exception=True,
            )
        except Exception:
            _logger.warning(
                "WhatsApp: impossible to format incoming number %s", number
            )
            return False, False, False, False
        if not number or not formatted_number:
            return False, False, False, False

        region_data = phone_validation.phone_get_region_data_for_number(
            formatted_number
        )
        return (
            formatted_number,
            region_data["code"],
            str(region_data["national_number"]),
            int(region_data["phone_code"]),
        )

    def _find_from_number(self, number):
        formatted_number, _country_code, national_number, _phone_code = (
            self._parse_whatsapp_number(number)
        )
        if not formatted_number:
            return self.env["res.partner"]
        intl_digits = re.sub(r"\D", "", formatted_number)
        partners = self._search_partner_from_whatsapp_number(
            formatted_number, national_number, intl_digits
        )
        if partners:
            return self._prefer_whatsapp_partner(partners)
        return self.env["res.partner"]

    def _get_whatsapp_partner_category(self):
        """Return the contact tag used for partners created from WhatsApp."""
        return self.env.ref(
            "mail_whatsapp.res_partner_category_whatsapp",
            raise_if_not_found=False,
        ) or self.env["res.partner.category"]

    def _find_or_create_from_number(self, number, name=False):
        partner = self._find_from_number(number)
        if partner:
            return partner

        formatted_number, number_country_code, _national, number_phone_code = (
            self._parse_whatsapp_number(number)
        )
        if not formatted_number:
            return self.env["res.partner"]

        country = self.env["res.country"].search(
            [("phone_code", "=", number_phone_code)]
        )
        if len(country) > 1:
            country = country.filtered(
                lambda c: c.code.lower() == number_country_code.lower()
            )
        vals = {
            "country_id": country.id if country and len(country) == 1 else False,
            "mobile": formatted_number,
            "name": name or formatted_number,
        }
        whatsapp_category = self._get_whatsapp_partner_category()
        if whatsapp_category:
            vals["category_id"] = [Command.set(whatsapp_category.ids)]
        partners = self.env["res.partner"].create(vals)
        partners._message_log(
            body=_("Partner created by incoming WhatsApp message.")
        )
        return partners[0]

    def _search_partner_from_whatsapp_number(
        self, formatted_number, national_number, intl_digits
    ):
        partners = self._search_on_phone_mobile("=", formatted_number)
        if not partners:
            partners = self._search_on_phone_mobile("=like", national_number)
        if not partners and intl_digits:
            partners = self._search_on_phone_mobile_digits(intl_digits)
        if not partners and national_number:
            partners = self._search_on_phone_mobile_digits(national_number)
        if not partners and "phone_sanitized" in self._fields:
            partners = self.sudo().search(
                [("phone_sanitized", "=", formatted_number)], order="id"
            )
        return partners

    def _prefer_whatsapp_partner(self, partners):
        """Prefer a real contact over an auto-created WhatsApp partner."""
        if len(partners) == 1:
            return partners[0]

        def _looks_like_phone_name(partner):
            name_digits = re.sub(r"\D", "", partner.name or "")
            phone_digits = re.sub(r"\D", "", partner.phone or "")
            mobile_digits = re.sub(r"\D", "", partner.mobile or "")
            if not name_digits:
                return True
            return name_digits in {phone_digits, mobile_digits} or (
                partner.name or ""
            ).strip() in {
                partner.phone or "",
                partner.mobile or "",
            }

        named = partners.filtered(lambda p: not _looks_like_phone_name(p))
        candidates = named or partners
        return candidates.sorted(key=lambda p: p.id)[0]

    def _search_on_phone_mobile(self, operator, number):
        assert operator in {"=", "=like"}
        number = number.strip()
        if not number:
            return self.browse()
        if len(number) < self.env["mail.thread.phone"]._phone_search_min_length:
            raise exceptions.UserError(
                _(
                    "Please enter at least 3 characters when searching a "
                    "Phone/Mobile number."
                )
            )

        phone_fields = ["mobile", "phone"]
        pattern = r"[\s\\./\(\)\-]"
        sql_operator = "LIKE" if operator == "=like" else "="

        if number.startswith(("+", "00")):
            where_str = " OR ".join(
                f"""partner.{phone_field} IS NOT NULL AND (
                        REGEXP_REPLACE(partner.{phone_field}, %s, '', 'g') {sql_operator} %s OR
                        REGEXP_REPLACE(partner.{phone_field}, %s, '', 'g') {sql_operator} %s
                )"""
                for phone_field in phone_fields
            )
            query = (
                f"SELECT partner.id FROM {self._table} partner "
                f"WHERE {where_str} ORDER BY partner.id;"
            )
            term = re.sub(pattern, "", number[1 if number.startswith("+") else 2 :])
            if operator == "=like":
                term = f"%{term}"
            self._cr.execute(
                query, (pattern, "00" + term, pattern, "+" + term) * len(phone_fields)
            )
        else:
            where_str = " OR ".join(
                f"(partner.{phone_field} IS NOT NULL AND "
                f"REGEXP_REPLACE(partner.{phone_field}, %s, '', 'g') "
                f"{sql_operator} %s)"
                for phone_field in phone_fields
            )
            query = (
                f"SELECT partner.id FROM {self._table} partner "
                f"WHERE {where_str} ORDER BY partner.id;"
            )
            term = re.sub(pattern, "", number)
            if operator == "=like":
                term = f"%{term}"
            self._cr.execute(query, (pattern, term) * len(phone_fields))
        res = self._cr.fetchall()
        return self.browse([r[0] for r in res])

    def _search_on_phone_mobile_digits(self, digits):
        """Match phone/mobile by digits only (ignores spaces, dashes, +)."""
        digits = re.sub(r"\D", "", digits or "")
        if len(digits) < self.env["mail.thread.phone"]._phone_search_min_length:
            return self.browse()

        phone_fields = ["mobile", "phone"]
        where_str = " OR ".join(
            f"""partner.{phone_field} IS NOT NULL AND (
                REGEXP_REPLACE(partner.{phone_field}, '[^0-9]', '', 'g') = %s
                OR REGEXP_REPLACE(partner.{phone_field}, '[^0-9]', '', 'g') LIKE %s
            )"""
            for phone_field in phone_fields
        )
        query = (
            f"SELECT partner.id FROM {self._table} partner "
            f"WHERE {where_str} ORDER BY partner.id;"
        )
        like_term = f"%{digits}"
        self._cr.execute(query, (digits, like_term) * len(phone_fields))
        return self.browse([r[0] for r in self._cr.fetchall()])

    def action_open_partner_wa_channels(self):
        return {
            "name": _("WhatsApp Chats"),
            "type": "ir.actions.act_window",
            "domain": [
                ("channel_type", "=", "whatsapp"),
                ("channel_partner_ids", "in", self.ids),
            ],
            "res_model": "discuss.channel",
            "view_mode": "list,form",
        }
