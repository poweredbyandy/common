1. Install **Document Templates**.
2. Ensure `wkhtmltopdf` is available on the server (same requirement as
   every Odoo PDF report).
3. With `workers = 0`, set system parameter `report.url` to
   `http://127.0.0.1:<http_port>` (the module sets this on install if
   missing). Without it, PDF download hangs because wkhtmltopdf cannot
   fetch report assets from the same process.
4. Open **Document Templates** and create a template for the target
   model.
5. Optionally set a paper format and whether to wrap the page with the
   company external layout.
6. Use **Add to Print menu** so users can print from records of that
   model.

Templates render without the restricted QWeb mode, like email templates:
any user who can print gets the full template (expressions, loops and
conditions). Saving dynamic content requires the **Document Templates /
Administrator** group, which implies **Mail Template Editor**.
