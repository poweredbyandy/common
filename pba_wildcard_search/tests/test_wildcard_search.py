from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestWildcardSearch(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {
                "name": "MOTOR DE CARRO 350",
                "list_price": 100.0,
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "MOTOR DE CARRO 350",
            }
        )

    def test_product_wildcard_search(self):
        products = self.env["product.product"].search(
            [("name", "ilike", "Motor*350")]
        )
        self.assertIn(self.product, products)

    def test_partner_wildcard_search(self):
        partners = self.env["res.partner"].search(
            [("name", "ilike", "Motor*350")]
        )
        self.assertIn(self.partner, partners)

    def test_name_search_wildcard(self):
        results = self.env["product.product"].name_search("Motor*350", limit=10)
        self.assertTrue(any(record_id == self.product.id for record_id, _ in results))

    def test_wildcard_no_match(self):
        products = self.env["product.product"].search(
            [("name", "ilike", "Motor*999")]
        )
        self.assertNotIn(self.product, products)

    def test_plain_search_still_works(self):
        products = self.env["product.product"].search(
            [("name", "ilike", "MOTOR")]
        )
        self.assertIn(self.product, products)
