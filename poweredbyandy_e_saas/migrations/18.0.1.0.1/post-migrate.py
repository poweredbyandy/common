from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
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
