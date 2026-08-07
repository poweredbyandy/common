from markupsafe import escape, Markup

from odoo import http
from odoo.http import request


def _company_name():
    company = request.env.company.sudo()
    return company.name or "the service provider"


def _base_url():
    return request.env["ir.config_parameter"].sudo().get_param(
        "web.base.url", ""
    ).rstrip("/") or (request.httprequest.url_root or "").rstrip("/")


def _legal_page(title, body_html):
    company = escape(_company_name())
    title_esc = escape(title)
    html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <meta name="robots" content="index,follow"/>
  <title>{title_esc} — {company}</title>
  <style>
    body {{
      font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
      line-height: 1.55;
      color: #1a1a1a;
      max-width: 760px;
      margin: 0 auto;
      padding: 2rem 1.25rem 3rem;
      background: #fff;
    }}
    h1 {{ font-size: 1.75rem; margin-bottom: 0.25rem; }}
    h2 {{ font-size: 1.15rem; margin-top: 1.75rem; }}
    p, li {{ color: #333; }}
    .meta {{ color: #666; font-size: 0.9rem; margin-bottom: 1.5rem; }}
    nav a {{ margin-right: 1rem; }}
    a {{ color: #0b5fff; }}
  </style>
</head>
<body>
  <nav>
    <a href="/mail_whatsapp/legal/terms">Terms of Service</a>
    <a href="/mail_whatsapp/legal/privacy">Privacy Policy</a>
    <a href="/mail_whatsapp/legal/data-deletion">User Data Deletion</a>
  </nav>
  <h1>{title_esc}</h1>
  <p class="meta">Applies to the WhatsApp integration operated by {company}.</p>
  {body_html}
</body>
</html>
"""
    return request.make_response(
        html,
        headers=[
            ("Content-Type", "text/html; charset=utf-8"),
            ("Cache-Control", "public, max-age=300"),
        ],
    )


class MailWhatsappLegalController(http.Controller):

    @http.route(
        "/mail_whatsapp/legal/terms",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        website=False,
    )
    def terms_of_service(self, **kwargs):
        """Public Terms of Service page for Meta App Dashboard."""
        company = escape(_company_name())
        body = Markup(
            f"""
  <p>
    These Terms of Service (“Terms”) govern use of the WhatsApp messaging
    features provided through the software operated by <strong>{company}</strong>
    (“we”, “us”), including connection of WhatsApp Business accounts via Meta
    Embedded Signup / Facebook Login for Business.
  </p>
  <h2>1. Acceptance</h2>
  <p>
    By connecting a WhatsApp Business Account, authorizing our Meta application,
    or using the messaging features, you agree to these Terms and to Meta’s
    applicable Platform Terms, WhatsApp Business Terms, and policies.
  </p>
  <h2>2. Service description</h2>
  <p>
    We provide software that lets authorized business users send and receive
    WhatsApp messages, synchronize conversation history when coexistence is
    enabled, and manage WhatsApp Business Account credentials linked to our
    Meta application.
  </p>
  <h2>3. Eligibility and accounts</h2>
  <p>
    You must have authority to connect the WhatsApp Business Account and Meta
    Business assets you authorize. You are responsible for safeguarding access
    to your Odoo / business accounts and for activity performed under those
    credentials.
  </p>
  <h2>4. Acceptable use</h2>
  <ul>
    <li>Comply with WhatsApp Commerce and Business policies and applicable law.</li>
    <li>Do not spam, harass, or send unlawful content through WhatsApp.</li>
    <li>Do not attempt to bypass Meta rate limits, security, or consent requirements.</li>
    <li>Do not misuse Facebook Login or Platform data beyond the stated purposes.</li>
  </ul>
  <h2>5. Third-party platforms</h2>
  <p>
    WhatsApp and Facebook Login are services of Meta Platforms, Inc. Your use of
    those services is also subject to Meta’s terms. We are not responsible for
    Meta outages, policy changes, or suspension of your WhatsApp / Meta assets.
  </p>
  <h2>6. Data and privacy</h2>
  <p>
    How we process personal data is described in our
    <a href="/mail_whatsapp/legal/privacy">Privacy Policy</a>. Instructions to
    request deletion are available at
    <a href="/mail_whatsapp/legal/data-deletion">User Data Deletion</a>.
  </p>
  <h2>7. Disclaimer</h2>
  <p>
    The service is provided on an “as available” basis. To the maximum extent
    permitted by law, we disclaim warranties of uninterrupted availability or
    fitness for a particular purpose.
  </p>
  <h2>8. Limitation of liability</h2>
  <p>
    To the maximum extent permitted by law, {company} shall not be liable for
    indirect, incidental, or consequential damages arising from use of the
    WhatsApp integration or Meta platform features.
  </p>
  <h2>9. Changes</h2>
  <p>
    We may update these Terms. The current version will remain available at this
    public URL. Continued use after changes constitutes acceptance of the updated
    Terms where permitted by law.
  </p>
  <h2>10. Contact</h2>
  <p>
    For questions about these Terms, contact {company} using the contact details
    published on your business website or support channels.
  </p>
"""
        )
        return _legal_page("Terms of Service", body)

    @http.route(
        "/mail_whatsapp/legal/privacy",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        website=False,
    )
    def privacy_policy(self, **kwargs):
        """Public Privacy Policy page required by Meta Platform Terms §4."""
        company = escape(_company_name())
        deletion_callback = escape(
            f"{_base_url()}/mail_whatsapp/facebook/data_deletion"
        )
        body = Markup(
            f"""
  <p>
    This Privacy Policy explains what data <strong>{company}</strong> processes
    when you use our WhatsApp integration connected through Meta (Facebook Login
    for Business / WhatsApp Cloud API / Embedded Signup).
  </p>
  <h2>1. Data we process</h2>
  <ul>
    <li>
      <strong>Facebook / Meta identity data:</strong> app-scoped user ID and
      basic profile information granted via Facebook Login (for example
      <code>public_profile</code> and <code>email</code> when authorized).
    </li>
    <li>
      <strong>WhatsApp Business assets:</strong> WhatsApp Business Account ID,
      phone number ID, display phone number, access tokens, and configuration
      needed to send/receive messages.
    </li>
    <li>
      <strong>Messaging content:</strong> inbound and outbound WhatsApp messages,
      media metadata, delivery statuses, and, when coexistence is enabled,
      message echoes and chat history synchronized from the WhatsApp Business App.
    </li>
    <li>
      <strong>Contact data:</strong> phone numbers and related partner records
      created or matched in our system to operate conversations.
    </li>
  </ul>
  <h2>2. Purposes of processing</h2>
  <ul>
    <li>Authenticate your Meta / WhatsApp Business connection.</li>
    <li>Send and receive WhatsApp customer service and business messages.</li>
    <li>Synchronize coexistence history and app state when enabled.</li>
    <li>Secure the service (signature verification, token validation, audit).</li>
    <li>Comply with Meta Platform Terms and applicable privacy laws.</li>
  </ul>
  <h2>3. Sharing</h2>
  <p>
    Message delivery uses Meta / WhatsApp infrastructure. We do not sell personal
    data. Data may be processed by hosting providers that support our software
    under appropriate confidentiality and security controls.
  </p>
  <h2>4. Retention</h2>
  <p>
    We retain WhatsApp credentials and conversation data while the integration
    remains active and as needed for business, security, and legal obligations.
    When you disconnect the app or request deletion, we delete or anonymize
    Facebook-linked credentials and related identifiable data as described below.
  </p>
  <h2 id="deletion">5. How to request deletion of your data</h2>
  <p>
    You may request deletion of data associated with our Meta application in
    any of these ways:
  </p>
  <ul>
    <li>
      From Facebook: Settings &amp; privacy → Settings → Apps and websites →
      remove the app and submit a data deletion request. Meta will call our
      data deletion callback (<code>{deletion_callback}</code>), and we will
      return a confirmation code and status URL.
    </li>
    <li>
      Follow the instructions on our
      <a href="/mail_whatsapp/legal/data-deletion">User Data Deletion</a> page.
    </li>
    <li>
      Contact {company} support and request deletion of your WhatsApp / Facebook
      linked data.
    </li>
  </ul>
  <h2>6. Your rights</h2>
  <p>
    Depending on your jurisdiction, you may have rights to access, correct, or
    delete personal data, or to object to certain processing. Use the deletion
    channels above or contact {company}.
  </p>
  <h2>7. Security</h2>
  <p>
    We use access controls, HTTPS endpoints, and Meta signature verification for
    webhooks and signed requests. No method of transmission or storage is
    completely secure.
  </p>
  <h2>8. Changes</h2>
  <p>
    We may update this Privacy Policy. The current version remains available at
    this public, non-geoblocked URL so Meta crawlers and users can access it.
  </p>
  <h2>9. Contact</h2>
  <p>
    Privacy requests: contact {company} through your usual business support
    channels.
  </p>
"""
        )
        return _legal_page("Privacy Policy", body)

    @http.route(
        "/mail_whatsapp/legal/data-deletion",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        website=False,
    )
    def user_data_deletion_instructions(self, **kwargs):
        """User Data Deletion instructions URL for Meta App Dashboard."""
        company = escape(_company_name())
        body = Markup(
            f"""
  <p>
    This page explains how users can request deletion of data that
    <strong>{company}</strong> obtained through our Meta / WhatsApp application.
  </p>
  <h2>Option 1 — Request from Facebook</h2>
  <ol>
    <li>Open Facebook → Settings &amp; privacy → Settings → Apps and websites.</li>
    <li>Locate our app, remove it, then open removed apps/websites.</li>
    <li>Click <strong>Send Request</strong> for data deletion.</li>
    <li>
      Meta notifies our systems. You receive a confirmation code and a status
      URL where you can track the request.
    </li>
  </ol>
  <h2>Option 2 — Contact us</h2>
  <p>
    Contact {company} support, identify the Facebook user / WhatsApp Business
    number involved, and request deletion of associated data. We will confirm
    when credentials and linked identifiable Facebook data have been removed or
    anonymized, or explain if no matching data was found.
  </p>
  <h2>What we delete</h2>
  <ul>
    <li>Stored WhatsApp access tokens and Facebook app-scoped user linkage.</li>
    <li>Active connection of the related WhatsApp Business account in our app.</li>
    <li>
      Other personal data tied to that Facebook user to the extent reasonably
      identifiable in our records, subject to legal retention obligations.
    </li>
  </ul>
  <p>
    See also our <a href="/mail_whatsapp/legal/privacy">Privacy Policy</a>.
  </p>
"""
        )
        return _legal_page("User Data Deletion Instructions", body)
