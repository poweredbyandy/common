def _ensure_report_url(env):
    """Avoid wkhtmltopdf deadlocks when Odoo runs with workers=0.

    wkhtmltopdf fetches report assets from the HTTP server. Without
    ``report.url`` pointing at a reachable URL (typically 127.0.0.1),
    the single-threaded server blocks forever and the PDF never downloads.
    """
    icp = env["ir.config_parameter"].sudo()
    if icp.get_param("report.url"):
        return
    base = icp.get_param("web.base.url") or "http://127.0.0.1:8069"
    report_url = base.replace("localhost", "127.0.0.1")
    # Prefer loopback so headless wkhtmltopdf can reach the same process.
    if "://" not in report_url:
        report_url = "http://127.0.0.1:8069"
    icp.set_param("report.url", report_url)


def post_init_hook(env):
    _ensure_report_url(env)
