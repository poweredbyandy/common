import base64
import os
import re

from odoo import _
from odoo.exceptions import ValidationError

from odoo.addons.payment_pagomovil.const import MAX_RECEIPT_BYTES, PAGOMOVIL_BANKS

_RIF_KIND_DIGIT = {
    "V": 1,
    "E": 2,
    "J": 3,
    "C": 3,
    "P": 4,
    "G": 5,
}
_RIF_MULTIPLIERS = (3, 2, 7, 6, 5, 4, 3, 2)
_RECEIPT_SIGNATURES = (
    (b"%PDF", ".pdf"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"\xff\xd8\xff", ".jpg"),
)


def normalize_vat(vat):
    """Return a compact Venezuelan RIF or cédula, or raise ValidationError."""
    compact = re.sub(r"[^A-Za-z0-9]", "", vat or "").upper()
    if compact.startswith("VE") and re.fullmatch(r"VE[VEJGCP]\d{6,9}", compact):
        compact = compact[2:]
    if re.fullmatch(r"[VE]\d{6}", compact) or re.fullmatch(r"[VEJGCP]\d{7,8}", compact):
        return compact
    if re.fullmatch(r"[VEJGCP]\d{9}", compact):
        if _rif_checksum_ok(compact):
            return compact
        raise ValidationError(_("El dígito verificador del RIF no es válido."))
    raise ValidationError(
        _(
            "Indique el RIF o la cédula de quien envía el pago. "
            "Ejemplo: V12345678 o J-12345678-4."
        )
    )


def normalize_phone(phone):
    """Return an 11-digit Venezuelan mobile number, or raise ValidationError."""
    digits = re.sub(r"\D", "", phone or "")
    if digits.startswith("58"):
        digits = digits[2:]
    if len(digits) == 10 and digits.startswith("4"):
        digits = "0" + digits
    if not re.fullmatch(r"04(12|14|16|24|26)\d{7}", digits):
        raise ValidationError(
            _("Indique un teléfono móvil venezolano. Ejemplo: 04141234567.")
        )
    return digits


def normalize_bank(bank_code):
    """Return the Venezuelan bank code, or raise ValidationError."""
    code = (bank_code or "").strip()
    if code not in dict(PAGOMOVIL_BANKS):
        raise ValidationError(_("Seleccione el banco desde el que envió el pago."))
    return code


def normalize_reference(reference):
    """Return the bank reference without spaces or dashes."""
    compact = re.sub(r"[\s-]", "", reference or "")
    if not re.fullmatch(r"[A-Za-z0-9]{4,20}", compact):
        raise ValidationError(
            _(
                "Indique la referencia del pago "
                "(de 4 a 20 letras o números)."
            )
        )
    return compact


def prepare_receipt(raw, filename):
    """Return the receipt as base64 and a safe filename."""
    if not raw:
        raise ValidationError(_("Adjunte el comprobante del pago."))
    if len(raw) > MAX_RECEIPT_BYTES:
        raise ValidationError(
            _("El comprobante supera el tamaño máximo de 5 MB.")
        )
    extension = _receipt_extension(raw)
    if not extension:
        raise ValidationError(
            _("El comprobante debe ser un archivo JPG, PNG, WEBP o PDF.")
        )
    name = os.path.basename(filename or "")
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)[:80]
    if not name or name in {".", ".."}:
        name = "comprobante" + extension
    elif not name.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".pdf")):
        name += extension
    return base64.b64encode(raw), name


def _rif_checksum_ok(compact):
    kind_digit = _RIF_KIND_DIGIT[compact[0]]
    identifier = compact[1:9]
    check_digit = int(compact[9])
    checksum = kind_digit * 4
    checksum += sum(
        int(digit) * weight for digit, weight in zip(identifier, _RIF_MULTIPLIERS)
    )
    checksum_digit = 11 - (checksum % 11)
    if checksum_digit > 9:
        checksum_digit = 0
    return check_digit == checksum_digit


def _receipt_extension(raw):
    if len(raw) >= 12 and raw.startswith(b"RIFF") and raw[8:12] == b"WEBP":
        return ".webp"
    for signature, extension in _RECEIPT_SIGNATURES:
        if raw.startswith(signature):
            return extension
    return None
