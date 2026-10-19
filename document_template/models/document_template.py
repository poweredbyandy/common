import base64
import binascii
import logging

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.mail import is_html_empty

from ..tools.docx import docx_to_html
from ..tools.markdown import markdown_to_html

_logger = logging.getLogger(__name__)

# Google Docs–like defaults (mm)
MARGIN_NORMAL = 25.4
MARGIN_NARROW = 12.7
MARGIN_MODERATE_LR = 19.05
MARGIN_WIDE_LR = 50.8


class DocumentTemplate(models.Model):
    _name = "document.template"
    _description = "Document Template"
    _inherit = ["mail.render.mixin"]
    _order = "name, id"
    _unrestricted_rendering = True

    name = fields.Char(
        required=True,
        translate=True,
        default=lambda self: _("Untitled document"),
    )
    active = fields.Boolean(default=True)
    model_id = fields.Many2one(
        "ir.model",
        string="Applies to",
        ondelete="set null",
        domain=[("transient", "=", False)],
    )
    model = fields.Char(
        related="model_id.model",
        string="Related Document Model",
        store=True,
        readonly=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    header_html = fields.Html(
        string="Header",
        render_engine="qweb",
        render_options={"post_process": True},
        sanitize="email_outgoing",
        translate=True,
        prefetch=True,
    )
    body_html = fields.Html(
        string="Body",
        render_engine="qweb",
        render_options={"post_process": True},
        sanitize="email_outgoing",
        translate=True,
        prefetch=True,
    )
    footer_html = fields.Html(
        string="Footer",
        render_engine="qweb",
        render_options={"post_process": True},
        sanitize="email_outgoing",
        translate=True,
        prefetch=True,
    )
    paperformat_id = fields.Many2one(
        "report.paperformat",
        string="Paper Format",
        default=lambda self: self.env.ref(
            "base.paperformat_euro",
            raise_if_not_found=False,
        ),
        help="Page size and orientation. Margins are configured separately.",
    )
    report_paperformat_id = fields.Many2one(
        "report.paperformat",
        string="Report Paper Format",
        copy=False,
        ondelete="set null",
        help="Private paper format used by the print action, including margins.",
    )
    margin_top = fields.Float(
        string="Top Margin (mm)",
        default=MARGIN_NORMAL,
        required=True,
    )
    margin_bottom = fields.Float(
        string="Bottom Margin (mm)",
        default=MARGIN_NORMAL,
        required=True,
    )
    margin_left = fields.Float(
        string="Left Margin (mm)",
        default=MARGIN_NORMAL,
        required=True,
    )
    margin_right = fields.Float(
        string="Right Margin (mm)",
        default=MARGIN_NORMAL,
        required=True,
    )
    header_height = fields.Float(
        string="Header Height (mm)",
        default=20.0,
        required=True,
        help="Space reserved for the header on each printed page.",
    )
    footer_height = fields.Float(
        string="Footer Height (mm)",
        default=15.0,
        required=True,
        help="Space reserved for the footer on each printed page.",
    )
    show_page_numbers = fields.Boolean(
        string="Show Page Numbers",
        default=True,
        help="Display the page number in the printed footer.",
    )
    page_number_format = fields.Selection(
        selection=[
            ("page_of_total", "1 / 3"),
            ("page_of_total_label", "Page 1 of 3"),
            ("page_only", "1"),
            ("page_only_label", "Page 1"),
            ("dash_page", "- 1 -"),
        ],
        string="Page Number Format",
        default="page_of_total",
        required=True,
    )
    page_number_align = fields.Selection(
        selection=[
            ("left", "Left"),
            ("center", "Center"),
            ("right", "Right"),
        ],
        string="Page Number Alignment",
        default="center",
        required=True,
    )
    use_company_layout = fields.Boolean(
        string="Use Company Layout",
        help="Wrap the document with the company external layout "
        "(header, footer and logo).",
    )
    report_id = fields.Many2one(
        "ir.actions.report",
        string="Print Report",
        readonly=True,
        copy=False,
        ondelete="set null",
    )
    report_view_id = fields.Many2one(
        "ir.ui.view",
        string="Report View",
        readonly=True,
        copy=False,
        ondelete="set null",
    )
    has_print_action = fields.Boolean(
        compute="_compute_has_print_action",
    )

    @api.depends("report_id")
    def _compute_has_print_action(self):
        for template in self:
            template.has_print_action = bool(template.report_id)

    @api.depends("model")
    def _compute_render_model(self):
        for template in self:
            template.render_model = template.model

    def write(self, vals):
        res = super().write(vals)
        sync_fields = {
            "model_id",
            "name",
            "paperformat_id",
            "margin_top",
            "margin_bottom",
            "margin_left",
            "margin_right",
            "header_height",
            "footer_height",
            "show_page_numbers",
            "page_number_format",
            "page_number_align",
        }
        if sync_fields & set(vals):
            self.filtered("report_id")._sync_report_action()
        return res

    def unlink(self):
        reports = self.mapped("report_id")
        views = self.mapped("report_view_id")
        paperformats = self.mapped("report_paperformat_id")
        res = super().unlink()
        reports.sudo().unlink()
        views.sudo().unlink()
        paperformats.sudo().unlink()
        return res

    def _render_record_html(self, record, field_name="body_html"):
        self.ensure_one()
        if field_name not in ("header_html", "body_html", "footer_html"):
            raise UserError(_("Invalid document section: %s", field_name))
        if not record or is_html_empty(self[field_name]):
            return Markup("")
        rendered = self._render_field(field_name, [record.id]).get(record.id, "")
        return Markup(rendered or "")

    def _has_header(self):
        self.ensure_one()
        return not is_html_empty(self.header_html)

    def _has_footer(self):
        self.ensure_one()
        return not is_html_empty(self.footer_html) or self.show_page_numbers

    def _page_number_markup(self):
        """Return QWeb-ready markup for the configured page number format."""
        self.ensure_one()
        fmt = self.page_number_format or "page_of_total"
        if fmt == "page_of_total_label":
            return Markup('Page <span class="page"/> of <span class="topage"/>')
        if fmt == "page_only":
            return Markup('<span class="page"/>')
        if fmt == "page_only_label":
            return Markup('Page <span class="page"/>')
        if fmt == "dash_page":
            return Markup('- <span class="page"/> -')
        return Markup('<span class="page"/> / <span class="topage"/>')

    def action_add_print(self):
        from ..hooks import _ensure_report_url

        _ensure_report_url(self.env)
        for template in self:
            if template.report_id:
                continue
            if not template.model_id:
                raise UserError(_("Select a model before adding the print action."))
            template._create_report_action()
        return True

    def action_download_pdf(self):
        """Print the template PDF for a sample / contextual record."""
        self.ensure_one()
        from ..hooks import _ensure_report_url

        _ensure_report_url(self.env)
        if not self.model_id or not self.model:
            raise UserError(
                _("Select a model in File → Page setup before downloading the PDF.")
            )
        if not self.report_id:
            self.action_add_print()
        record = self.env[self.model].search([], limit=1)
        if not record:
            raise UserError(
                _("Create at least one %s record before downloading the PDF.")
                % (self.model_id.name or self.model)
            )
        return self.report_id.report_action(record)

    def action_remove_print(self):
        for template in self:
            template._remove_report_action()
        return True

    def action_open_preview(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Template Preview"),
            "res_model": "document.template.preview",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": {
                "default_document_template_id": self.id,
            },
        }

    @api.model
    def convert_markdown_to_html(self, content):
        """Convert Markdown source to rich HTML for the document body."""
        if content is None:
            return ""
        if not isinstance(content, str):
            raise UserError(_("Markdown content must be text."))
        return markdown_to_html(content)

    @api.model
    def convert_docx_to_html(self, content_b64):
        """Convert a Word/Google Docs .docx (base64) to rich HTML."""
        if not content_b64:
            return ""
        if not isinstance(content_b64, str):
            raise UserError(_("DOCX content must be base64 text."))
        try:
            raw = base64.b64decode(content_b64)
        except (binascii.Error, ValueError) as err:
            raise UserError(_("Invalid DOCX file.")) from err
        try:
            return docx_to_html(raw)
        except ImportError as err:
            raise UserError(
                _(
                    "Install the Python package 'mammoth' to import "
                    "Word / Google Docs (.docx) files."
                )
            ) from err
        except Exception as err:
            _logger.exception("DOCX import failed")
            raise UserError(
                _("Could not convert the DOCX file: %s") % err
            ) from err

    def _report_xml_id(self):
        self.ensure_one()
        return "document_template.report_%s" % self.id

    def _get_margin_values(self):
        self.ensure_one()
        header_h = self.header_height or 0.0
        footer_h = self.footer_height or 0.0
        # wkhtmltopdf reserves margin-top/bottom for header/footer bands.
        margin_top = max(self.margin_top or 0.0, header_h)
        margin_bottom = max(self.margin_bottom or 0.0, footer_h)
        return {
            "margin_top": margin_top,
            "margin_bottom": margin_bottom,
            "margin_left": self.margin_left,
            "margin_right": self.margin_right,
            "header_spacing": int(round(header_h or margin_top or 0)),
        }

    def _ensure_report_paperformat(self):
        """Build or update a private paperformat with page size + template margins."""
        self.ensure_one()
        base = self.paperformat_id
        values = {
            "name": _("Document Template: %s") % (self.name or self.id),
            "default": False,
            "format": base.format if base else "A4",
            "page_height": base.page_height if base else 0,
            "page_width": base.page_width if base else 0,
            "orientation": base.orientation if base else "Portrait",
            "header_line": False,
            "dpi": base.dpi if base else 90,
            "css_margins": True,
            "disable_shrinking": base.disable_shrinking if base else False,
        }
        values.update(self._get_margin_values())
        PaperFormat = self.env["report.paperformat"].sudo()
        if self.report_paperformat_id:
            self.report_paperformat_id.write(values)
        else:
            paperformat = PaperFormat.create(values)
            self.sudo().write({"report_paperformat_id": paperformat.id})
        return self.report_paperformat_id

    def _create_report_action(self):
        self.ensure_one()
        report_name = self._report_xml_id()
        paperformat = self._ensure_report_paperformat()
        view = self.env["ir.ui.view"].sudo().create(
            {
                "name": "Document Template: %s" % self.name,
                "type": "qweb",
                "key": report_name,
                "arch": (
                    '<t t-name="%s">'
                    '<t t-call="document_template.report_document">'
                    '<t t-set="document_template_id" t-value="%s"/>'
                    "</t>"
                    "</t>"
                )
                % (report_name, self.id),
            }
        )
        report = (
            self.env["ir.actions.report"]
            .sudo()
            .create(
                {
                    "name": self.name,
                    "model": self.model,
                    "report_type": "qweb-pdf",
                    "report_name": report_name,
                    "report_file": report_name,
                    "print_report_name": self._get_print_report_name_expr(),
                    "binding_model_id": self.model_id.id,
                    "binding_type": "report",
                    "paperformat_id": paperformat.id,
                }
            )
        )
        self.sudo().write(
            {
                "report_id": report.id,
                "report_view_id": view.id,
            }
        )

    def _get_print_report_name_expr(self):
        self.ensure_one()
        return (
            "(object.env['document.template'].browse(%s).name or 'Document')"
            " + ' - ' + (object.display_name or '')"
        ) % self.id

    def _remove_report_action(self):
        self.ensure_one()
        report = self.report_id.sudo()
        view = self.report_view_id.sudo()
        paperformat = self.report_paperformat_id.sudo()
        self.sudo().write(
            {
                "report_id": False,
                "report_view_id": False,
                "report_paperformat_id": False,
            }
        )
        if report:
            report.unlink()
        if view:
            view.unlink()
        if paperformat:
            paperformat.unlink()

    def _sync_report_action(self):
        for template in self.filtered("report_id"):
            if not template.model_id:
                template._remove_report_action()
                continue
            paperformat = template._ensure_report_paperformat()
            report = template.report_id.sudo()
            report.write(
                {
                    "name": template.name,
                    "model": template.model,
                    "binding_model_id": template.model_id.id,
                    "paperformat_id": paperformat.id,
                    "print_report_name": template._get_print_report_name_expr(),
                }
            )
            if template.report_view_id:
                template.report_view_id.sudo().write(
                    {
                        "name": "Document Template: %s" % template.name,
                    }
                )
