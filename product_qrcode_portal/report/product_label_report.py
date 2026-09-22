from odoo import models


class ReportProductTemplateLabel2x7(models.AbstractModel):
    _inherit = "report.product.report_producttemplatelabel2x7"

    def _get_report_values(self, docids, data):
        website_id = (data or {}).get("portal_qr_website_id")
        if website_id:
            self = self.with_context(portal_qr_website_id=int(website_id))
        return super()._get_report_values(docids, data)


class ReportProductTemplateLabel4x7(models.AbstractModel):
    _inherit = "report.product.report_producttemplatelabel4x7"

    def _get_report_values(self, docids, data):
        website_id = (data or {}).get("portal_qr_website_id")
        if website_id:
            self = self.with_context(portal_qr_website_id=int(website_id))
        return super()._get_report_values(docids, data)


class ReportProductTemplateLabel4x12(models.AbstractModel):
    _inherit = "report.product.report_producttemplatelabel4x12"

    def _get_report_values(self, docids, data):
        website_id = (data or {}).get("portal_qr_website_id")
        if website_id:
            self = self.with_context(portal_qr_website_id=int(website_id))
        return super()._get_report_values(docids, data)


class ReportProductTemplateLabel4x12NoPrice(models.AbstractModel):
    _inherit = "report.product.report_producttemplatelabel4x12noprice"

    def _get_report_values(self, docids, data):
        website_id = (data or {}).get("portal_qr_website_id")
        if website_id:
            self = self.with_context(portal_qr_website_id=int(website_id))
        return super()._get_report_values(docids, data)


class ReportProductTemplateLabelDymo(models.AbstractModel):
    _inherit = "report.product.report_producttemplatelabel_dymo"

    def _get_report_values(self, docids, data):
        website_id = (data or {}).get("portal_qr_website_id")
        if website_id:
            self = self.with_context(portal_qr_website_id=int(website_id))
        return super()._get_report_values(docids, data)
