import base64
import hashlib
import hmac
import json
import logging

_logger = logging.getLogger(__name__)


def base64_url_decode(value):
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def parse_signed_request(signed_request, app_secret):
    """Parse and validate Meta signed_request payload."""
    if not signed_request or not app_secret or "." not in signed_request:
        return None
    encoded_sig, payload = signed_request.split(".", 1)
    try:
        signature = base64_url_decode(encoded_sig)
        data = json.loads(base64_url_decode(payload).decode("utf-8"))
    except (ValueError, TypeError, json.JSONDecodeError) as err:
        _logger.warning("Invalid Facebook signed_request payload: %s", err)
        return None

    expected_sig = hmac.new(
        app_secret.encode("utf-8"),
        msg=payload.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(signature, expected_sig):
        _logger.warning("Bad Facebook signed_request signature")
        return None
    return data
