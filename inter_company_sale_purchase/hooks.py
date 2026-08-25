def post_init_hook(env):
    companies = env["res.company"].sudo().search([])
    companies.write(
        {
            "ic_so_from_po": True,
            "ic_po_from_so": True,
            "ic_invoice_mode": "draft",
            "ic_picking_mode": "none",
        }
    )
