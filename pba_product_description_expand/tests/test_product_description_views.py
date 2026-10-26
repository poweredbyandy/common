from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestProductDescriptionViews(TransactionCase):
    def _arch(self, model, view_xmlid=None):
        view_id = self.env.ref(view_xmlid).id if view_xmlid else None
        return self.env[model].get_view(view_id=view_id, view_type="form")["arch"]

    def test_product_form_enlarges_the_description_fields(self):
        arch = self._arch("product.template")
        self.assertIn("{'height': 250}", arch)
        self.assertIn('name="description_sale"', arch)
        self.assertIn('name="description_purchase"', arch)
        self.assertEqual(arch.count("pba_product_description"), 2)
        self.assertIn('rows="10"', arch)

    def test_document_forms_enlarge_the_line_description(self):
        for model in ("sale.order", "purchase.order", "account.move"):
            arch = self._arch(model)
            self.assertIn("pba_product_description", arch)
            self.assertIn('rows="10"', arch)
        line_arch = self._arch(
            "purchase.order.line", "purchase.purchase_order_line_form2"
        )
        self.assertIn("pba_product_description", line_arch)
        self.assertIn('rows="10"', line_arch)
