from lxml import etree

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProductDescriptionExpand(TransactionCase):
    def _form_arch(self, model):
        view = self.env[model].get_view(view_type="form")
        return etree.fromstring(view["arch"])

    def _assert_expanded_field(self, node, rows="10"):
        self.assertIsNotNone(node)
        classes = node.get("class") or ""
        self.assertIn("o_pba_expanded_description", classes)
        self.assertEqual(node.get("rows"), rows)

    def test_product_template_form_expands_descriptions(self):
        arch = self._form_arch("product.template")
        form_class = arch.get("class") or ""
        self.assertIn("o_pba_product_description_expand", form_class)

        description = arch.xpath("//field[@name='description']")[0]
        self.assertIn("o_pba_expanded_description", description.get("class") or "")
        options = description.get("options") or ""
        self.assertIn("height", options)
        self.assertIn("250", options)

        description_sale = arch.xpath("//field[@name='description_sale']")[0]
        self._assert_expanded_field(description_sale)

        description_purchase = arch.xpath("//field[@name='description_purchase']")
        self.assertTrue(description_purchase)
        self._assert_expanded_field(description_purchase[0])

        for fname in (
            "description_pickingin",
            "description_pickingout",
            "description_picking",
        ):
            nodes = arch.xpath(f"//field[@name='{fname}']")
            self.assertTrue(nodes, f"Missing {fname} on product form")
            self._assert_expanded_field(nodes[0])

    def test_product_variant_form_reuses_expanded_template_view(self):
        arch = self._form_arch("product.product")
        form_class = arch.get("class") or ""
        self.assertIn("o_pba_product_description_expand", form_class)
        description_sale = arch.xpath("//field[@name='description_sale']")[0]
        self._assert_expanded_field(description_sale)

    def test_sale_order_line_form_expands_description(self):
        arch = self._form_arch("sale.order")
        name_field = arch.xpath("//field[@name='order_line']/form/field[@name='name']")[0]
        self._assert_expanded_field(name_field)

    def test_purchase_order_line_form_expands_description(self):
        arch = self._form_arch("purchase.order")
        name_field = arch.xpath(
            "//field[@name='order_line']/form//page[@name='notes']/field[@name='name']"
        )[0]
        self._assert_expanded_field(name_field)

    def test_invoice_line_form_expands_description(self):
        arch = self._form_arch("account.move")
        name_field = arch.xpath(
            "//field[@name='invoice_line_ids']/form//field[@name='name'][@widget='text']"
        )[0]
        self._assert_expanded_field(name_field)
