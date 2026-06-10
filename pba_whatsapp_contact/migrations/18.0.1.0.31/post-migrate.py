import logging

import requests
from werkzeug.urls import url_join

from odoo.addons.mail_gateway_whatsapp.models.mail_gateway import BASE_URL

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    Template = env["mail.whatsapp.template"].with_context(active_test=False)
    for template in Template.search([("template_uid", "!=", False)]):
        gateway = template.gateway_id
        if not gateway or not gateway.token:
            continue
        template_url = url_join(
            BASE_URL,
            f"v{gateway.whatsapp_version}/{template.template_uid}",
        )
        try:
            response = requests.get(
                template_url,
                headers={"Authorization": f"Bearer {gateway.token}"},
                timeout=10,
            )
            response.raise_for_status()
            json_data = response.json()
        except Exception as err:
            _logger.warning(
                "No se pudo sincronizar botones Meta para plantilla %s: %s",
                template.id,
                err,
            )
            continue
        template.write(
            {
                "pba_meta_url_button_count": Template._pba_count_meta_dynamic_url_buttons(
                    json_data
                )
            }
        )
