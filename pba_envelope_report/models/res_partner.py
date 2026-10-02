from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _envelope_phone(self):
        """Phone text for the envelope.

        Uses the partner's own phone/mobile and, when empty, falls back to the
        commercial partner (a delivery contact usually has no phone of its own).
        """
        partner = self[:1]
        if not partner:
            return ""
        commercial = partner.commercial_partner_id
        phones = []
        for own, fallback in (
            (partner.phone, commercial.phone),
            (partner.mobile, commercial.mobile),
        ):
            value = (own or fallback or "").strip()
            if value and value not in phones:
                phones.append(value)
        return " / ".join(phones)
