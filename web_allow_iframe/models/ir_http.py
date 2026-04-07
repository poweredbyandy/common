from odoo import models


class IrHttpIframe(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _post_dispatch(cls, response):
        super()._post_dispatch(response)
        if not hasattr(response, "headers"):
            return

        response.headers.pop("X-Frame-Options", None)

        csp = response.headers.get("Content-Security-Policy", "")
        if "frame-ancestors" in csp:
            parts = [
                d.strip()
                for d in csp.split(";")
                if "frame-ancestors" not in d
            ]
            parts.append("frame-ancestors *")
            response.headers["Content-Security-Policy"] = "; ".join(
                p for p in parts if p
            )

        cookies_raw = response.headers.getlist("Set-Cookie")
        if cookies_raw:
            patched = []
            for cookie in cookies_raw:
                if cookie.startswith("session_id="):
                    cookie = "session_id_h" + cookie[len("session_id"):]
                if "SameSite" not in cookie:
                    cookie += "; SameSite=None; Secure"
                else:
                    cookie = cookie.replace(
                        "SameSite=Lax", "SameSite=None"
                    ).replace("SameSite=Strict", "SameSite=None")
                    if "Secure" not in cookie:
                        cookie += "; Secure"
                patched.append(cookie)
            response.headers.remove("Set-Cookie")
            for cookie in patched:
                response.headers.add("Set-Cookie", cookie)
