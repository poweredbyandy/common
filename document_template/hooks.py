def _ensure_report_url(env):
    """Avoid wkhtmltopdf deadlocks when Odoo runs with workers=0.

    wkhtmltopdf fetches report assets from the HTTP server. A missing
    ``report.url``, a ``localhost`` host, or a loopback port that is not
    the one this process binds makes that download wait forever.
    """
    from urllib.parse import urlparse

    from odoo.tools import config

    icp = env["ir.config_parameter"].sudo()
    http_port = config.get("http_port") or 8069
    expected = "http://127.0.0.1:%s" % http_port
    current = icp.get_param("report.url") or ""
    parsed = urlparse(current) if current else None
    current_port = None
    if parsed is not None and parsed.hostname:
        current_port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if not current or (
        parsed is not None
        and parsed.hostname in ("localhost", "127.0.0.1", "::1")
        and str(current_port) != str(http_port)
    ):
        icp.set_param("report.url", expected)
    base = icp.get_param("web.base.url") or ""
    if "://localhost" in base:
        icp.set_param(
            "web.base.url",
            base.replace("://localhost", "://127.0.0.1", 1),
        )



def post_init_hook(env):
    _ensure_report_url(env)
