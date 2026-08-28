# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestPbaWebReportError(HttpCase):
    def test_report_routes_wraps_user_error(self):
        self.authenticate("admin", "admin")

        def _raise_user_error(*args, **kwargs):
            raise UserError("Cannot print this report")

        self.patch(
            type(self.env["ir.actions.report"]),
            "_render_qweb_pdf",
            _raise_user_error,
        )
        response = self.url_open("/report/pdf/pba.dummy_report/1")
        self.assertEqual(response.status_code, 500)
        self.assertIn("Cannot print this report", response.text)
