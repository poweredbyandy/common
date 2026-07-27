import logging

from odoo import SUPERUSER_ID, api

from odoo.addons.pba_custom_seller.hooks import _migrate_pricelist_and_users

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _migrate_pricelist_and_users(env)
