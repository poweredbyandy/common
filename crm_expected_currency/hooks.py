def post_init_hook(env):
    """Las oportunidades ya cargadas quedan en la moneda de su compañía."""
    leads = env["crm.lead"].with_context(active_test=False).search([])
    for lead in leads:
        currency = lead.company_currency or lead.company_id.currency_id or env.company.currency_id
        lead.with_context(skip_expected_currency_sync=True).write({
            "expected_currency_id": currency.id,
            "expected_revenue_currency": lead.expected_revenue or 0.0,
        })
