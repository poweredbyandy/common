from odoo.tools import LazyTranslate

_lt = LazyTranslate(__name__)


class WhatsAppError(Exception):
    def __init__(self, message="", error_code=False, failure_type=False):
        self.failure_type = failure_type
        self.error_code = error_code
        self.error_message = message

        if error_code:
            formated_message = f"{error_code}: {message}"
        elif failure_type == "account":
            formated_message = _lt(
                "WhatsApp account is misconfigured."
            )
        elif failure_type == "network":
            formated_message = _lt(
                "WhatsApp could not be reached or the query was malformed."
            )
        elif message:
            formated_message = message
        else:
            formated_message = _lt(
                "Unknown error when processing WhatsApp request."
            )

        super().__init__(formated_message)
