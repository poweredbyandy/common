from lxml import etree

from odoo import api

PARTNER_AUTOCOMPLETE_VIEW_FIELDS = ("partner_gid", "additional_info")


def post_init_hook(env):
    _remove_products_menu(env)
    _disable_partner_autocomplete_integration(env)
    _enable_settings(env)


def _disable_partner_autocomplete_integration(env):
    module = env["ir.module.module"].search(
        [("name", "=", "partner_autocomplete")], limit=1
    )
    if module and module.state == "installed":
        module.button_immediate_uninstall()
    _cleanup_partner_autocomplete_views(env)


def _cleanup_partner_autocomplete_views(env):
    if "partner_gid" in env["res.partner"]._fields:
        return
    views = env["ir.ui.view"].sudo().search(
        [
            ("model", "in", ("res.partner", "res.company")),
            ("arch_db", "ilike", "partner_gid"),
        ]
    )
    for view in views:
        _strip_fields_from_view_arch(view, PARTNER_AUTOCOMPLETE_VIEW_FIELDS)


def _strip_fields_from_view_arch(view, field_names):
    arch = view.arch_db
    if not arch:
        return
    try:
        root = etree.fromstring(arch.encode("utf-8"))
    except etree.XMLSyntaxError:
        return
    changed = False
    for field_name in field_names:
        for node in root.xpath(f".//field[@name='{field_name}']"):
            parent = node.getparent()
            if parent is not None:
                parent.remove(node)
                changed = True
    if changed:
        view.arch_db = etree.tostring(root, encoding="unicode")


def _remove_products_menu(env):
    xml_ids = [
        'poweredbyandy_e_saas.menu_poweredbyandy_root',
        'poweredbyandy_e_saas.menu_poweredbyandy_products_parent',
        'poweredbyandy_e_saas.menu_poweredbyandy_products',
        'poweredbyandy_e_saas.menu_poweredbyandy_variants',
        'poweredbyandy_e_saas.menu_poweredbyandy_attributes',
        'poweredbyandy_e_saas.menu_poweredbyandy_pricelists',
        'poweredbyandy_e_saas.action_all_products',
        'poweredbyandy_e_saas.action_all_variants',
    ]
    for xml_id in xml_ids:
        record = env.ref(xml_id, raise_if_not_found=False)
        if record:
            record.unlink()


def _enable_settings(env):
    group_user = env.ref('base.group_user')
    groups_to_enable = [
        'account.group_delivery_invoice_address',
        'account.group_warning_account',
        'uom.group_uom',
        'product.group_product_variant',
        'product.group_product_pricelist',
        'sale.group_discount_per_so_line',
        'sale.group_warning_sale',
        'sale.group_proforma_sales',
        'sale_management.group_sale_order_template',
        'stock.group_stock_multi_locations',
        'stock.group_adv_location',
        'stock.group_production_lot',
    ]

    for xml_id in groups_to_enable:
        group = env.ref(xml_id, raise_if_not_found=False)
        if group and group not in group_user.implied_ids:
            group_user.implied_ids |= group

    env['ir.config_parameter'].sudo().set_param(
        'account.use_invoice_terms', True
    )
    companies = env['res.company'].sudo().search([])
    companies.write({
        'terms_type': 'plain',
        'display_invoice_tax_company_currency': True,
    })

    env['ir.default'].sudo().set(
        'product.template', 'purchase_method', 'purchase'
    )

    mto_route = env.ref('stock.route_warehouse0_mto', raise_if_not_found=False)
    if mto_route and not mto_route.active:
        mto_route.active = True
