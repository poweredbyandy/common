from lxml import etree

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPbaDocumentLayout(TransactionCase):
    def test_document_layout_preview(self):
        layout = self.env["base.document.layout"].create(
            {"company_id": self.env.company.id}
        )
        layout.report_layout_id = self.env.ref(
            "pba_web_external_layout.report_layout_pba_presupuesto"
        )

        layout._compute_preview()

        self.assertTrue(layout.preview)
        self.assertIn("o_pba_presupuesto_pdf_header", layout.preview)
        self.assertIn("o_report_layout_pba_presupuesto", layout.preview)
        self.assertIn("o_pba_document_grid", layout.preview)
        self.assertIn('name="invoice_date"', layout.preview)
        self.assertIn('name="due_date"', layout.preview)
        self.assertIn("line-height: 1.2", layout.preview)
        self.assertIn("background: transparent", layout.preview)
        self.assertNotIn("PRESUPUESTO -", layout.preview)

    def test_document_layout_uses_selected_font(self):
        layout = self.env["base.document.layout"].create(
            {"company_id": self.env.company.id}
        )
        layout.report_layout_id = self.env.ref(
            "pba_web_external_layout.report_layout_pba_presupuesto"
        )
        layout.font = "Oswald"

        css = layout._get_css_for_preview(layout._get_asset_style(), layout.id)

        self.assertIn("font-family: Oswald", css)

    def test_document_layout_uses_custom_background(self):
        layout = self.env["base.document.layout"].create(
            {
                "company_id": self.env.company.id,
                "layout_background": "Custom",
                "layout_background_image": b"cGJhLWJhY2tncm91bmQ=",
            }
        )
        layout.report_layout_id = self.env.ref(
            "pba_web_external_layout.report_layout_pba_presupuesto"
        )

        layout._compute_preview()

        self.assertIn("o_report_layout_background", layout.preview)
        self.assertIn(
            "data:image/png;base64,cGJhLWJhY2tncm91bmQ=", layout.preview
        )

    def test_standard_layout_keeps_sale_information(self):
        customer = self.env["res.partner"].create({"name": "Standard Customer"})
        order = self.env["sale.order"].create({"partner_id": customer.id})
        self.env.company.external_report_layout_id = self.env.ref(
            "web.external_layout_standard"
        )

        report = self.env["ir.actions.report"]._render_qweb_html(
            "sale.report_saleorder", order.ids
        )[0]
        html = report.decode() if isinstance(report, bytes) else report

        self.assertIn('id="informations"', html)
        self.assertIn('name="informations_date"', html)

    def test_stock_reports_reposition_native_blocks(self):
        picking_arch = self.env.ref("stock.report_picking")._get_combined_arch()
        picking_arch_text = etree.tostring(picking_arch, encoding="unicode")
        delivery_arch = self.env.ref(
            "stock.report_delivery_document"
        )._get_combined_arch()
        delivery_arch_text = etree.tostring(delivery_arch, encoding="unicode")

        self.assertIn("stock_address_block", picking_arch_text)
        self.assertIn("stock_information_block", picking_arch_text)
        self.assertIn("document_information_block", picking_arch_text)
        self.assertIn("document_information_block", delivery_arch_text)
        self.assertIn("layout_document_title", delivery_arch_text)

    def test_sale_information_blocks_keep_native_content(self):
        self.env.company.report_header = "PBA Tagline"
        self.env.company.company_details = False
        self.env.company.street = "PBA Company Street"
        customer = self.env["res.partner"].create({"name": "PBA Customer"})
        invoice_address = self.env["res.partner"].create(
            {
                "name": "PBA Invoice Address",
                "parent_id": customer.id,
                "type": "invoice",
            }
        )
        shipping_address = self.env["res.partner"].create(
            {
                "name": "PBA Shipping Address",
                "parent_id": customer.id,
                "type": "delivery",
            }
        )
        order = self.env["sale.order"].create(
            {
                "partner_id": customer.id,
                "partner_invoice_id": invoice_address.id,
                "partner_shipping_id": shipping_address.id,
            }
        )
        self.env.company.external_report_layout_id = self.env.ref(
            "pba_web_external_layout.external_layout_pba_presupuesto"
        )

        report = self.env["ir.actions.report"]._render_qweb_html(
            "sale.report_saleorder", order.ids
        )[0]
        html = report.decode() if isinstance(report, bytes) else report

        self.assertIn("o_pba_client_information", html)
        self.assertIn("o_pba_shipping_information", html)
        self.assertIn("o_pba_document_information", html)
        self.assertIn("PBA Company Street", html)
        self.assertLess(html.index("PBA Tagline"), html.index("PBA Company Street"))
        self.assertIn("PBA Customer", html)
        self.assertIn("PBA Shipping Address", html)
        self.assertIn('name="informations_date"', html)
