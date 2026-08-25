# -*- coding: utf-8 -*-

from odoo import models


class ProductLabelLayout(models.TransientModel):
    _inherit = "product.label.layout"

    def _prepare_report_data(self):
        xml_id, data = super()._prepare_report_data()
        if "zpl" in (self.print_format or ""):
            xml_id = "pba_product_label.action_report_label_product_product"
        return xml_id, data
