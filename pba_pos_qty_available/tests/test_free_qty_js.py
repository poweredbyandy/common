import shutil

import odoo.tests


@odoo.tests.tagged("post_install", "-at_install")
class TestPbaPosQtyAvailableJs(odoo.tests.HttpCase):
    def test_free_qty_hoot_unit(self):
        """Run Hoot suite for free_qty utils in a real browser when available."""
        chrome_bins = (
            "google-chrome",
            "chromium",
            "chromium-browser",
            "google-chrome-stable",
        )
        if not any(shutil.which(bin_name) for bin_name in chrome_bins):
            self.skipTest("Chrome/Chromium is required to run Hoot browser tests")
        self.browser_js(
            "/web/tests?headless&loglevel=2&preset=desktop&timeout=15000"
            "&filter=pba_pos_qty_available free_qty utils",
            "",
            "",
            login="admin",
            timeout=180,
            success_signal="[HOOT] Test suite succeeded",
        )
