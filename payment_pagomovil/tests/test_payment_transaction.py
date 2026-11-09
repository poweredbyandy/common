import base64

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.payment.tests.common import PaymentCommon
from odoo.addons.payment_pagomovil.const import MAX_RECEIPT_BYTES
from odoo.addons.payment_pagomovil.models.pagomovil import (
    normalize_bank,
    normalize_phone,
    normalize_reference,
    normalize_vat,
    prepare_receipt,
)

MINI_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@tagged("post_install", "-at_install")
class TestPagoMovil(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = cls._prepare_provider(
            code="pagomovil",
            update_values={
                "pagomovil_phone": "04141234567",
                "pagomovil_vat": "J-12345678-4",
                "pagomovil_bank": "Banesco",
                "pagomovil_holder": "Compañía de prueba",
            },
        )
        cls.payment_method = cls.env.ref("payment_pagomovil.payment_method_pagomovil")
        cls.payment_method_id = cls.payment_method.id
        cls.payment_method_code = cls.payment_method.code

    def test_normalize_vat_accepts_cedula_and_rif(self):
        self.assertEqual(normalize_vat("V7440703"), "V7440703")
        self.assertEqual(normalize_vat("v-12.345.678"), "V12345678")
        self.assertEqual(normalize_vat("J-12345678-4"), "J123456784")
        self.assertEqual(normalize_vat("VEJ123456784"), "J123456784")

    def test_normalize_vat_rejects_bad_check_digit(self):
        with self.assertRaises(ValidationError):
            normalize_vat("J123456789")

    def test_normalize_phone_and_reference(self):
        self.assertEqual(normalize_phone("0414-1234567"), "04141234567")
        self.assertEqual(normalize_phone("+58 414 1234567"), "04141234567")
        self.assertEqual(normalize_phone("4141234567"), "04141234567")
        self.assertEqual(normalize_bank("0134"), "0134")
        self.assertEqual(normalize_reference("12 34-56"), "123456")
        with self.assertRaises(ValidationError):
            normalize_bank("9999")
        with self.assertRaises(ValidationError):
            normalize_phone("02121234567")
        with self.assertRaises(ValidationError):
            normalize_reference("12")

    def test_prepare_receipt_rejects_unknown_and_large_files(self):
        datas, name = prepare_receipt(MINI_PNG, "captura.png")
        self.assertTrue(datas)
        self.assertEqual(name, "captura.png")
        with self.assertRaises(ValidationError):
            prepare_receipt(b"not-a-receipt", "nota.txt")
        with self.assertRaises(ValidationError):
            prepare_receipt(b"\xff\xd8\xff" + (b"a" * MAX_RECEIPT_BYTES), "grande.jpg")

    def test_provider_normalizes_destination(self):
        self.provider.write({
            "pagomovil_phone": "0414-1234567",
            "pagomovil_vat": "J-12345678-4",
        })
        self.assertEqual(self.provider.pagomovil_phone, "04141234567")
        self.assertEqual(self.provider.pagomovil_vat, "J123456784")

    def test_register_sets_pending_and_blocks_the_same_reference(self):
        tx = self._create_transaction("direct")
        tx._pagomovil_register(
            "V12345678", "0414-1234567", "0134", "12 3456", MINI_PNG, "captura.png"
        )
        self.assertEqual(tx.state, "pending")
        self.assertEqual(tx.pagomovil_vat, "V12345678")
        self.assertEqual(tx.pagomovil_phone, "04141234567")
        self.assertEqual(tx.pagomovil_bank, "0134")
        self.assertEqual(tx.pagomovil_reference, "123456")
        self.assertEqual(tx.provider_reference, "123456")
        self.assertEqual(tx.pagomovil_destination_bank, "Banesco")
        self.assertEqual(tx.pagomovil_receipt_filename, "captura.png")

        other = self._create_transaction("direct", reference="Pago Movil 2")
        with self.assertRaises(ValidationError):
            other._pagomovil_register(
                "V12345678", "04141234567", "0134", "123456", MINI_PNG, "captura.png"
            )
        self.assertEqual(other.state, "draft")

        tx.action_pagomovil_set_canceled()
        self.assertEqual(tx.state, "cancel")
        other._pagomovil_register(
            "V12345678", "04141234567", "0102", "123456", MINI_PNG, "captura.png"
        )
        self.assertEqual(other.state, "pending")
        other.action_pagomovil_set_done()
        self.assertEqual(other.state, "done")
