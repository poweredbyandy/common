from markupsafe import escape

from odoo import _, http
from odoo.exceptions import AccessError, UserError
from odoo.http import request

from odoo.addons.mail_whatsapp.tools.meta_credentials import is_demo_environment


class MailWhatsappDemoReceiveController(http.Controller):

    def _check_access(self):
        if not request.env.user.has_group(
            "mail_whatsapp.group_mail_whatsapp_admin"
        ):
            raise AccessError(_("Only WhatsApp administrators can use this tool."))

    def _accounts(self):
        return request.env["mail.whatsapp.account"].sudo().search([])

    def _selected_account(self, wa_account_id=None):
        Account = request.env["mail.whatsapp.account"].sudo()
        if wa_account_id:
            try:
                account = Account.browse(int(wa_account_id)).exists()
            except (TypeError, ValueError):
                account = Account.browse()
            if account:
                return account
        if is_demo_environment(request.env):
            return Account.ensure_demo_account()
        return Account.search([], limit=1)

    def _account_options_html(self, account):
        rows = []
        for acc in self._accounts():
            selected = " selected" if account and acc.id == account.id else ""
            label = escape(
                "%s (%s)"
                % (
                    acc.name or acc.phone_uid,
                    acc.display_phone_number or acc.phone_uid,
                )
            )
            rows.append(
                '<option value="%s"%s>%s</option>'
                % (acc.id, selected, label)
            )
        if not rows:
            return '<option value="">No WhatsApp accounts</option>'
        return "\n".join(rows)

    def _render_page(
        self,
        *,
        account=None,
        sender_phone="584120000000",
        sender_name="Demo Customer",
        body="Hello Odoo, this is a simulated WhatsApp inbound message.",
        error="",
        success="",
        discuss_url="",
    ):
        account = account or self._selected_account()
        error_html = (
            '<div class="alert error">%s</div>' % escape(error) if error else ""
        )
        if success:
            link = ""
            if discuss_url:
                link = (
                    ' <a href="%s" target="_blank" rel="noopener">Open Discuss</a>'
                    % escape(discuss_url)
                )
            success_html = (
                '<div class="alert ok">%s%s</div>' % (escape(success), link)
            )
        else:
            success_html = ""

        html = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Simulate Incoming WhatsApp</title>
  <style>
    :root {
      --bg: #f4f6f8;
      --card: #fff;
      --text: #1f2a37;
      --muted: #6b7280;
      --line: #e5e7eb;
      --primary: #128c7e;
      --primary-dark: #0f6f64;
      --danger: #b42318;
      --ok: #067647;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
      background: linear-gradient(180deg, #e8f5f3 0%%, var(--bg) 240px);
      color: var(--text);
      min-height: 100vh;
      padding: 1.25rem;
    }
    .card {
      max-width: 520px;
      margin: 0 auto;
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 1.25rem 1.35rem 1.4rem;
      box-shadow: 0 10px 30px rgba(16, 24, 40, 0.08);
    }
    h1 { font-size: 1.25rem; margin: 0 0 0.35rem; }
    .sub { color: var(--muted); font-size: 0.92rem; margin-bottom: 1.1rem; }
    label {
      display: block;
      font-size: 0.85rem;
      font-weight: 600;
      margin: 0.85rem 0 0.35rem;
    }
    input, select, textarea {
      width: 100%%;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 0.65rem 0.75rem;
      font: inherit;
      background: #fff;
    }
    textarea { min-height: 110px; resize: vertical; }
    .actions {
      display: flex;
      gap: 0.6rem;
      margin-top: 1.15rem;
    }
    button {
      border: 0;
      border-radius: 10px;
      padding: 0.7rem 1rem;
      font: inherit;
      font-weight: 600;
      cursor: pointer;
    }
    button.primary {
      background: var(--primary);
      color: #fff;
      flex: 1;
    }
    button.primary:hover { background: var(--primary-dark); }
    button.ghost {
      background: #fff;
      border: 1px solid var(--line);
      color: var(--text);
    }
    .alert {
      border-radius: 10px;
      padding: 0.75rem 0.85rem;
      margin-bottom: 0.9rem;
      font-size: 0.92rem;
    }
    .alert.error {
      background: #fef3f2;
      color: var(--danger);
      border: 1px solid #fecdca;
    }
    .alert.ok {
      background: #ecfdf3;
      color: var(--ok);
      border: 1px solid #abefc6;
    }
    .alert a { color: inherit; font-weight: 700; }
  </style>
</head>
<body>
  <div class="card">
    <h1>Simulate Incoming WhatsApp</h1>
    <p class="sub">
      Movable browser window. Processes a fake inbound webhook in Odoo
      without calling Meta.
    </p>
    %(error)s
    %(success)s
    <form method="post" action="/mail_whatsapp/demo/simulate_receive">
      <input type="hidden" name="csrf_token" value="%(csrf)s"/>
      <label for="wa_account_id">WhatsApp Account</label>
      <select id="wa_account_id" name="wa_account_id" required>
        %(options)s
      </select>
      <label for="sender_phone">Sender Phone</label>
      <input id="sender_phone" name="sender_phone" value="%(phone)s"
             placeholder="584121234567" required/>
      <label for="sender_name">Sender Name</label>
      <input id="sender_name" name="sender_name" value="%(name)s"/>
      <label for="body">Incoming Message</label>
      <textarea id="body" name="body" required>%(body)s</textarea>
      <div class="actions">
        <button class="primary" type="submit">Simulate Incoming Message</button>
        <button class="ghost" type="button" onclick="window.close()">Close</button>
      </div>
    </form>
  </div>
</body>
</html>
""" % {
            "error": error_html,
            "success": success_html,
            "csrf": request.csrf_token(),
            "options": self._account_options_html(account),
            "phone": escape(sender_phone or ""),
            "name": escape(sender_name or ""),
            "body": escape(body or ""),
        }
        return request.make_response(
            html,
            headers=[("Content-Type", "text/html; charset=utf-8")],
        )

    @http.route(
        "/mail_whatsapp/demo/simulate_receive",
        type="http",
        auth="user",
        methods=["GET", "POST"],
        csrf=True,
        website=False,
    )
    def simulate_receive(self, **post):
        self._check_access()
        if request.httprequest.method == "GET":
            account = self._selected_account(
                request.params.get("wa_account_id") or post.get("wa_account_id")
            )
            return self._render_page(account=account)

        account = self._selected_account(post.get("wa_account_id"))
        values = {
            "account": account,
            "sender_phone": post.get("sender_phone") or "",
            "sender_name": post.get("sender_name") or "",
            "body": post.get("body") or "",
        }
        if not account:
            return self._render_page(
                error=_("Create or select a WhatsApp account first."),
                **values,
            )
        try:
            wizard = request.env["mail.whatsapp.test.receive"].sudo().create(
                {
                    "wa_account_id": account.id,
                    "sender_phone": values["sender_phone"],
                    "sender_name": values["sender_name"],
                    "body": values["body"],
                }
            )
            action = wizard.action_simulate_receive()
            active_id = (action.get("params") or {}).get("active_id") or ""
            channel_id = ""
            if isinstance(active_id, str) and "_" in active_id:
                channel_id = active_id.rsplit("_", 1)[-1]
            base = (
                request.env["ir.config_parameter"]
                .sudo()
                .get_param("web.base.url", "")
                .rstrip("/")
            )
            discuss_url = (
                f"{base}/odoo/action-mail.action_discuss?active_id={active_id}"
                if active_id
                else ""
            )
            return self._render_page(
                success=_(
                    "Inbound message simulated successfully%(suffix)s",
                    suffix=f" (channel {channel_id})." if channel_id else ".",
                ),
                discuss_url=discuss_url,
                **values,
            )
        except (UserError, AccessError) as err:
            return self._render_page(error=str(err), **values)
        except Exception as err:  # noqa: BLE001 - show in demo UI
            return self._render_page(error=str(err), **values)
