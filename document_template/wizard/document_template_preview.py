from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.mail import is_html_empty


class DocumentTemplatePreview(models.TransientModel):
    _name = "document.template.preview"
    _description = "Document Template Preview"

    @api.model
    def _selection_target_model(self):
        return [
            (model.model, model.name)
            for model in self.env["ir.model"].sudo().search([])
        ]

    document_template_id = fields.Many2one(
        "document.template",
        string="Document Template",
        required=True,
        ondelete="cascade",
    )
    model_id = fields.Many2one(
        related="document_template_id.model_id",
        string="Target Model",
    )
    resource_ref = fields.Reference(
        string="Record",
        selection="_selection_target_model",
        compute="_compute_resource_ref",
        readonly=False,
        store=True,
    )
    no_record = fields.Boolean(compute="_compute_no_record")
    header_html = fields.Html(
        string="Header",
        compute="_compute_preview_html",
        sanitize=False,
    )
    body_html = fields.Html(
        string="Body",
        compute="_compute_preview_html",
        sanitize=False,
    )
    footer_html = fields.Html(
        string="Footer",
        compute="_compute_preview_html",
        sanitize=False,
    )
    has_header = fields.Boolean(compute="_compute_preview_html")
    has_footer = fields.Boolean(compute="_compute_preview_html")
    error_msg = fields.Char(compute="_compute_preview_html")

    @api.depends("document_template_id", "document_template_id.model_id")
    def _compute_no_record(self):
        for preview in self:
            model = preview.document_template_id.model_id
            if not model:
                preview.no_record = True
                continue
            try:
                preview.no_record = not bool(
                    self.env[model.model].search([], limit=1)
                )
            except Exception:
                preview.no_record = True

    @api.depends("document_template_id")
    def _compute_resource_ref(self):
        for preview in self:
            model = preview.document_template_id.model_id
            if not model:
                preview.resource_ref = False
                continue
            # Keep the user's pick when it already matches the template model.
            current = preview.resource_ref
            if current and current._name == model.model:
                continue
            record = self.env[model.model].search([], limit=1)
            preview.resource_ref = (
                "%s,%s" % (model.model, record.id) if record else False
            )

    @api.depends("document_template_id", "resource_ref")
    def _compute_preview_html(self):
        for preview in self:
            preview.error_msg = False
            template = preview.document_template_id
            preview.has_header = bool(template and template._has_header())
            preview.has_footer = bool(template and template._has_footer())
            if not template:
                preview.header_html = False
                preview.body_html = False
                preview.footer_html = False
                continue
            if not preview.resource_ref:
                preview.header_html = template.header_html
                preview.body_html = template.body_html
                preview.footer_html = template.footer_html
                continue
            try:
                preview.header_html = template._render_record_html(
                    preview.resource_ref, "header_html"
                )
                preview.body_html = template._render_record_html(
                    preview.resource_ref, "body_html"
                )
                preview.footer_html = template._render_record_html(
                    preview.resource_ref, "footer_html"
                )
            except Exception as error:
                preview.header_html = template.header_html
                preview.body_html = template.body_html
                preview.footer_html = template.footer_html
                preview.error_msg = str(error)
                if is_html_empty(preview.body_html):
                    preview.body_html = False

    def action_download_pdf(self):
        self.ensure_one()
        template = self.document_template_id
        if not template:
            raise UserError(_("Select a document template first."))
        if not self.resource_ref:
            raise UserError(_("Select a test record before downloading the PDF."))
        if not template.report_id:
            template.action_add_print()
        return template.report_id.report_action(self.resource_ref)
