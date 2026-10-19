import base64
import io
import zipfile

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, tagged


def _minimal_docx_bytes(paragraph_text):
    """Build a tiny valid DOCX (OOXML zip) for conversion tests."""
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        "<w:p><w:r><w:t>%s</w:t></w:r></w:p>"
        '<w:tbl>'
        "<w:tr>"
        '<w:tc>'
        "<w:tcPr>"
        '<w:gridSpan w:val="2"/>'
        '<w:shd w:val="clear" w:fill="1B2A4A"/>'
        "</w:tcPr>"
        "<w:p><w:r>"
        '<w:rPr><w:b/><w:color w:val="FFFFFF"/></w:rPr>'
        "<w:t>CASILLA N1 HEADER</w:t>"
        "</w:r></w:p>"
        "</w:tc>"
        "</w:tr>"
        "<w:tr>"
        "<w:tc><w:p><w:r><w:rPr><w:b/></w:rPr>"
        "<w:t>Denominacion social</w:t></w:r></w:p></w:tc>"
        "<w:tc><w:p><w:r><w:t>RIF</w:t></w:r></w:p></w:tc>"
        "</w:tr>"
        "<w:tr>"
        "<w:tc><w:p><w:r><w:rPr><w:b/></w:rPr>"
        "<w:t>Teléfonos / correo</w:t></w:r></w:p></w:tc>"
        '<w:tc>'
        "<w:tcPr>"
        '<w:shd w:val="clear" w:fill="D6EAF8"/>'
        "</w:tcPr>"
        "<w:p/>"
        "</w:tc>"
        "</w:tr>"
        "</w:tbl>"
        "</w:body>"
        "</w:document>"
    ) % paragraph_text
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>'
        "</Relationships>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("word/document.xml", document_xml)
    return buf.getvalue()


@tagged("post_install", "-at_install")
class TestDocumentTemplate(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Document Template Partner",
            }
        )
        cls.partner_model = cls.env["ir.model"]._get("res.partner")
        cls.template = cls.env["document.template"].create(
            {
                "name": "Partner Letter",
                "model_id": cls.partner_model.id,
                "header_html": (
                    '<p>Header <t t-out="object.name"/></p>'
                ),
                "body_html": (
                    '<p>Hello <t t-out="object.name"/></p>'
                ),
                "footer_html": (
                    '<p>Footer <t t-out="object.email or \'\'"/></p>'
                ),
            }
        )

    def test_render_body_with_record_data(self):
        html = self.template._render_record_html(self.partner)
        self.assertIn("Document Template Partner", html)
        self.assertIn("Hello", html)

    def test_render_header_and_footer(self):
        header = self.template._render_record_html(self.partner, "header_html")
        footer = self.template._render_record_html(self.partner, "footer_html")
        self.assertIn("Header", header)
        self.assertIn("Document Template Partner", header)
        self.assertIn("Footer", footer)
        self.assertTrue(self.template._has_header())
        self.assertTrue(self.template._has_footer())

    def test_add_print_creates_report_bound_to_model(self):
        self.template.action_add_print()
        self.assertTrue(self.template.report_id)
        self.assertTrue(self.template.report_view_id)
        report = self.template.report_id
        self.assertEqual(report.model, "res.partner")
        self.assertEqual(report.binding_model_id, self.partner_model)
        self.assertEqual(report.report_type, "qweb-pdf")
        self.assertEqual(
            report.report_name,
            "document_template.report_%s" % self.template.id,
        )

    def test_convert_markdown_to_html(self):
        html = self.env["document.template"].convert_markdown_to_html(
            "# Title\n\nHello **world**\n\n- one\n- two\n"
        )
        self.assertIn("<h1>Title</h1>", html)
        self.assertIn("<strong>world</strong>", html)
        self.assertIn("<ul>", html)
        self.assertIn("<li>one</li>", html)
        self.assertIn("<li>two</li>", html)
        self.assertNotIn("**world**", html)
        self.assertNotIn("# Title", html)

    def test_convert_docx_to_html(self):
        raw = _minimal_docx_bytes("Google Docs sample")
        html = self.env["document.template"].convert_docx_to_html(
            base64.b64encode(raw).decode("ascii")
        )
        self.assertIn("Google Docs sample", html)
        self.assertNotIn("<w:t>", html)
        self.assertIn("<table", html)
        self.assertIn("border", html)
        self.assertIn("1B2A4A", html.upper())
        self.assertIn("D6EAF8", html.upper())
        self.assertIn("CASILLA", html)
        self.assertIn("Denominacion social", html)
        self.assertIn("<p><br/></p>", html)

    def test_convert_docx_keeps_content_control_text(self):
        from ..tools.docx import docx_to_html

        raw = _minimal_docx_bytes(
            'Tipo </w:t></w:r><w:sdt><w:sdtContent><w:r><w:t>☐</w:t></w:r>'
            "</w:sdtContent></w:sdt><w:r><w:t> Persona natural"
        )
        html = docx_to_html(raw)
        self.assertIn("Tipo ☐ Persona natural", html)

    def test_restricted_user_renders_dynamic_template(self):
        self.template.body_html = (
            '<p><t t-out="object.name.upper() if object.name else \'\'"/></p>'
        )
        user = self.env["res.users"].create(
            {
                "name": "Document Template Reader",
                "login": "document_template_reader",
                "groups_id": [
                    (6, 0, [self.env.ref("document_template.group_document_template_user").id])
                ],
            }
        )
        html = self.template.with_user(user)._render_record_html(
            self.partner.with_user(user)
        )
        self.assertIn("DOCUMENT TEMPLATE PARTNER", html)
        with self.assertRaises(AccessError):
            self.template.with_user(user).write(
                {"body_html": '<p><t t-out="object.email"/></p>'}
            )

    def test_margins_applied_to_report_paperformat(self):
        self.template.write(
            {
                "margin_top": 10.0,
                "margin_bottom": 15.0,
                "margin_left": 20.0,
                "margin_right": 25.0,
            }
        )
        self.template.action_add_print()
        paperformat = self.template.report_paperformat_id
        self.assertTrue(paperformat)
        self.assertEqual(paperformat.margin_top, 10.0)
        self.assertEqual(paperformat.margin_bottom, 15.0)
        self.assertEqual(paperformat.margin_left, 20.0)
        self.assertEqual(paperformat.margin_right, 25.0)
        self.assertEqual(self.template.report_id.paperformat_id, paperformat)
        self.template.write({"margin_top": 30.0})
        self.assertEqual(self.template.report_paperformat_id.margin_top, 30.0)

    def test_report_html_contains_rendered_body(self):
        self.template.action_add_print()
        report = self.template.report_id
        html, report_type = report._render_qweb_html(
            report,
            [self.partner.id],
        )
        self.assertEqual(report_type, "html")
        html_text = html.decode() if isinstance(html, bytes) else html
        self.assertIn("Document Template Partner", html_text)
        self.assertIn("Hello", html_text)
        self.assertIn("Header", html_text)
        self.assertIn("Footer", html_text)

    def test_remove_print_unlinks_report(self):
        self.template.action_add_print()
        report = self.template.report_id
        view = self.template.report_view_id
        self.template.action_remove_print()
        self.assertFalse(self.template.report_id)
        self.assertFalse(self.template.report_view_id)
        self.assertFalse(report.exists())
        self.assertFalse(view.exists())

    def test_pdf_when_wkhtmltopdf_available(self):
        self.template.action_add_print()
        Report = self.env["ir.actions.report"]
        if Report.get_wkhtmltopdf_state() == "install":
            self.skipTest("wkhtmltopdf is not installed")
        # wkhtmltopdf fetches report CSS/JS from the HTTP server. Without
        # report.url (or workers) that deadlocks in a single-threaded
        # TransactionCase waiting for itself.
        report_url = (
            self.env["ir.config_parameter"].sudo().get_param("report.url")
        )
        if not report_url:
            self.skipTest(
                "PDF rendering needs report.url to avoid wkhtmltopdf "
                "deadlocking on report assets during TransactionCase"
            )
        pdf, report_type = Report.with_context(
            force_report_rendering=True
        )._render_qweb_pdf(
            self.template.report_id.id,
            res_ids=[self.partner.id],
        )
        self.assertEqual(report_type, "pdf")
        self.assertTrue(pdf.startswith(b"%PDF"))
