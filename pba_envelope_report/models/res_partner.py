from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _envelope_address(self):
        """Address for the envelope using the full state name.

        Odoo's default country layout injects ``state_code`` (e.g. LR for Lara).
        That is a system format, not a typing error on the partner: the state is
        stored correctly on ``res.country.state``, with ``code`` = LR and
        ``name`` = Lara. This method reuses the country layout but prints the
        full name.
        """
        partner = self[:1]
        if not partner:
            return ""
        address_format, args = partner._prepare_display_address(without_company=True)
        args["state_code"] = args.get("state_name") or args.get("state_code") or ""
        return (address_format % args).strip()

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
