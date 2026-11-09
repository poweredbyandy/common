from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestCrmVat(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "Cliente CRM", "vat": "J-12345678-9", "is_company": True}
        )

    def test_lead_form_shows_vat_in_contact_information(self):
        arch = self.env["crm.lead"].get_view(view_type="form")["arch"]
        self.assertIn('name="vat"', arch)
        self.assertIn("Crear contacto", arch)
        self.assertIn("action_create_contact", arch)

    def test_partner_vat_fills_the_lead(self):
        lead = self.env["crm.lead"].create(
            {"name": "Oportunidad", "partner_id": self.partner.id}
        )
        self.assertEqual(lead.vat, "J-12345678-9")

    def test_lead_vat_updates_the_commercial_partner(self):
        contact = self.env["res.partner"].create(
            {"name": "Contacto", "parent_id": self.partner.id, "type": "contact"}
        )
        lead = self.env["crm.lead"].create(
            {"name": "Oportunidad", "partner_id": contact.id}
        )
        self.assertEqual(lead.vat, "J-12345678-9")
        lead.vat = "J-99999999-9"
        self.assertEqual(self.partner.vat, "J-99999999-9")
        self.assertEqual(contact.vat, "J-99999999-9")

    def test_new_customer_receives_the_lead_vat(self):
        lead = self.env["crm.lead"].create(
            {
                "name": "Oportunidad",
                "partner_name": "Empresa Nueva",
                "contact_name": "Ana",
                "vat": "J-55555555-5",
            }
        )
        company_values = lead._prepare_customer_values(
            "Empresa Nueva", is_company=True
        )
        contact_values = lead._prepare_customer_values(
            "Ana", is_company=False, parent_id=1
        )
        person_values = lead._prepare_customer_values("Ana", is_company=False)
        self.assertEqual(company_values["vat"], "J-55555555-5")
        self.assertNotIn("vat", contact_values)
        self.assertEqual(person_values["vat"], "J-55555555-5")

    def test_create_contact_from_lead_information(self):
        lead = self.env["crm.lead"].create(
            {
                "name": "Oportunidad sin cliente",
                "partner_name": "Empresa Nueva",
                "contact_name": "Ana",
                "email_from": "ana@example.com",
                "phone": "02121234567",
                "street": "Calle 1",
                "city": "Caracas",
                "vat": "J-55555555-5",
            }
        )
        lead.action_create_contact()
        contact = lead.partner_id
        self.assertEqual(contact.name, "Ana")
        self.assertEqual(contact.email, "ana@example.com")
        self.assertEqual(contact.phone, "02121234567")
        self.assertEqual(contact.street, "Calle 1")
        self.assertEqual(contact.city, "Caracas")
        self.assertEqual(contact.parent_id.name, "Empresa Nueva")
        self.assertTrue(contact.parent_id.is_company)
        self.assertEqual(contact.commercial_partner_id.vat, "J-55555555-5")
        self.assertEqual(lead.vat, "J-55555555-5")
        with self.assertRaises(UserError):
            lead.action_create_contact()

        person_lead = self.env["crm.lead"].create(
            {
                "name": "Persona sola",
                "contact_name": "Luis",
                "email_from": "luis@example.com",
                "vat": "V-12345678",
            }
        )
        person_lead.action_create_contact()
        self.assertEqual(person_lead.partner_id.name, "Luis")
        self.assertEqual(person_lead.partner_id.email, "luis@example.com")
        self.assertEqual(person_lead.partner_id.vat, "V-12345678")
        self.assertFalse(person_lead.partner_id.parent_id)
