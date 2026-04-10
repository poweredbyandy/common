import json
from urllib.parse import unquote_plus, urlparse

from werkzeug.exceptions import BadRequest
from werkzeug.urls import url_encode

from odoo import fields, http
from odoo.addons.web.controllers.utils import ensure_db
from odoo.http import request

SESSION_OAUTH_PENDING = "oauth_provider_pending_params"


def _is_loopback_host(hostname):
    if not hostname:
        return False
    h = hostname.lower()
    return h in ("localhost", "127.0.0.1", "::1") or h.startswith("127.")


def _origin_tuple(parsed):
    if not parsed.hostname:
        return None
    port = parsed.port
    if port is None:
        port = 443 if (parsed.scheme or "").lower() == "https" else 80
    return (parsed.scheme.lower(), parsed.hostname.lower(), port)


def _origins_equivalent(oa, ob):
    if oa is None or ob is None:
        return False
    if oa == ob:
        return True
    if oa[0] != ob[0] or oa[2] != ob[2]:
        return False
    ha, hb = oa[1], ob[1]
    if ha == hb:
        return True
    if _is_loopback_host(ha) and _is_loopback_host(hb):
        return True
    return False


def _parse_oauth_state_dict(state_param):
    if not state_param:
        return None
    raw = state_param.strip()
    variants = [raw, unquote_plus(raw)]
    for v in variants:
        for body in (v, v.replace("+", " ")):
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                continue
    return None


def _signin_url_from_oauth_state(state_param):
    st = _parse_oauth_state_dict(state_param)
    if not st:
        return None
    r_raw = st.get("r")
    if not isinstance(r_raw, str):
        return None
    r_url = r_raw
    for _ in range(8):
        n = unquote_plus(r_url)
        if n == r_url:
            break
        r_url = n
    if not r_url.startswith(("http://", "https://")):
        return None
    p = urlparse(r_url)
    if not p.netloc:
        return None
    return "%s://%s/auth_oauth/signin" % (p.scheme, p.netloc)


def _effective_oauth_redirect_uri(redirect_uri, fixed, fix_o, hom_o):
    """Elige la URL de retorno del flujo implícito (fragmento con access_token).

    Si ``redirect_uri`` apunta al mismo origen que el Homologado (copia errónea,
    ``web.base.url`` mal en el Origen, etc.) pero ``state.r`` indica el Origen,
    se usa el ``signin`` deducido de ``state`` para no enviar el token al propio
    Homologado.
    """
    ru_o = _origin_tuple(urlparse(redirect_uri))
    effective = redirect_uri
    relax_allowlist = False
    if not (
        fixed
        and fix_o
        and hom_o
        and not _origins_equivalent(fix_o, hom_o)
    ):
        return effective, relax_allowlist
    relax_allowlist = True
    if _origins_equivalent(ru_o, hom_o):
        effective = fixed
    elif _origins_equivalent(ru_o, fix_o):
        effective = redirect_uri
    else:
        effective = fixed
    return effective, relax_allowlist


class OauthProviderController(http.Controller):
    @http.route(
        ["/oauth_provider/authorize", "/oauth2/authorize"],
        type="http",
        auth="public",
        readonly=False,
        methods=["GET"],
    )
    def authorize(
        self,
        response_type=None,
        client_id=None,
        redirect_uri=None,
        scope=None,
        state=None,
        oauth_resume=None,
        oauth_pending_token=None,
        **kw,
    ):
        ensure_db()
        if oauth_resume and str(oauth_resume).strip().lower() in ("1", "true", "yes"):
            pending = request.session.pop(SESSION_OAUTH_PENDING, None)
            if (not pending or not isinstance(pending, dict)) and (
                oauth_pending_token or kw.get("oauth_pending_token")
            ):
                token = oauth_pending_token or kw.get("oauth_pending_token")
                pending = (
                    request.env["oauth.provider.pending"]
                    .sudo()
                    .consume(token)
                )
            if not pending or not isinstance(pending, dict):
                q = {}
                if request.session.db:
                    q["db"] = request.session.db
                next_url = (
                    "/web/login?%s" % url_encode(q) if q else "/web/login"
                )
                return request.redirect(next_url, 303)
            response_type = pending.get("response_type")
            client_id = pending.get("client_id")
            redirect_uri = pending.get("redirect_uri")
            scope = pending.get("scope")
            state = pending.get("state")

        if response_type != "token":
            raise BadRequest()
        if not client_id or not str(client_id).strip():
            return request.make_response(
                "Falta client_id. En el Odoo Origen: Ajustes > OAuth Odoo Client, "
                "rellene el ID de cliente (el mismo que en Clientes OAuth aquí).",
                status=400,
                headers=[("Content-Type", "text/plain; charset=utf-8")],
            )
        if not redirect_uri:
            raise BadRequest()
        root = request.httprequest.url_root
        client = request.env["oauth.provider.client"].sudo().get_by_client_id(client_id)
        if not client:
            raise BadRequest()

        hom_o = _origin_tuple(urlparse(root))
        fixed = _signin_url_from_oauth_state(state)
        fix_o = _origin_tuple(urlparse(fixed)) if fixed else None

        effective, relax_allowlist = _effective_oauth_redirect_uri(
            redirect_uri, fixed, fix_o, hom_o
        )

        if not client.is_redirect_allowed(effective) and not relax_allowlist:
            raise BadRequest()
        if not request.session.uid:
            pending_payload = {
                "response_type": response_type,
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": scope,
                "state": state,
            }
            request.session[SESSION_OAUTH_PENDING] = pending_payload
            request.session.touch()
            db_token = request.env["oauth.provider.pending"].sudo().create_from_payload(
                pending_payload
            )
            resume_qs = url_encode(
                {"oauth_resume": "1", "oauth_pending_token": db_token}
            )
            login_query = {
                "redirect": "/oauth_provider/authorize?%s" % resume_qs,
            }
            if request.session.db:
                login_query["db"] = request.session.db
            next_url = "/web/login?%s" % url_encode(login_query)
            resp = request.redirect(next_url, 303)
            resp.autocorrect_location_header = False
            return resp
        user = request.env["res.users"].sudo().browse(request.session.uid)
        tok_model = request.env["oauth.provider.token"].sudo()
        ttl = tok_model._get_access_token_ttl_seconds()
        token = tok_model.create_for_user(user, ttl_seconds=ttl)
        fragment = url_encode(
            {
                "access_token": token,
                "token_type": "Bearer",
                "expires_in": str(ttl),
                "state": state or "",
            }
        )
        location = "%s#%s" % (effective, fragment)
        resp = request.redirect(location, 303, local=False)
        resp.autocorrect_location_header = False
        return resp

    @http.route(
        ["/oauth_provider/tokeninfo", "/oauth2/tokeninfo"],
        type="http",
        auth="public",
        readonly=False,
        methods=["GET"],
    )
    def tokeninfo(self, access_token=None, **kw):
        ensure_db()
        if not access_token and request.httprequest.args.get("access_token"):
            access_token = request.httprequest.args.get("access_token")
        if not access_token:
            return request.make_json_response({"error": "invalid_request"}, status=400)
        request.env["oauth.provider.token"].sudo()._gc_expired()
        row = (
            request.env["oauth.provider.token"]
            .sudo()
            .search([("token", "=", access_token)], limit=1)
        )
        now = fields.Datetime.now()
        if not row or row.expires < now:
            return request.make_json_response({"error": "invalid_token"}, status=400)
        user = row.user_id.sudo()
        login = user.login
        email = user.email or login
        name = user.name or login
        payload = {
            "user_id": login,
            "email": email,
            "name": name,
        }
        return request.make_json_response(payload)
