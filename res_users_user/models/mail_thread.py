from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _get_message_create_valid_field_names(self):
        field_names = super()._get_message_create_valid_field_names()
        field_names.add("sub_user_id")
        return field_names

    def _message_create(self, values_list):
        sub_user_id = self.env.context.get("sub_user_id")
        if sub_user_id:
            for values in values_list:
                values.setdefault("sub_user_id", sub_user_id)
        return super()._message_create(values_list)
