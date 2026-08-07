import logging

_logger = logging.getLogger(__name__)

ENV_DEMO = "demo"
ENV_TEST = "test"
ENV_PRODUCTION = "production"
PARAM_ENVIRONMENT = "mail_whatsapp.meta_environment"
ALL_ENVIRONMENTS = (ENV_DEMO, ENV_TEST, ENV_PRODUCTION)


def get_meta_environment(env):
    value = (
        env["ir.config_parameter"]
        .sudo()
        .get_param(PARAM_ENVIRONMENT, ENV_TEST)
        or ENV_TEST
    )
    if value in ALL_ENVIRONMENTS:
        return value
    return ENV_TEST


def is_demo_environment(env):
    return get_meta_environment(env) == ENV_DEMO


def _environment_prefix(environment):
    if environment == ENV_PRODUCTION:
        return "production"
    if environment == ENV_DEMO:
        return "demo"
    return "test"


def get_meta_credentials(env, environment=None):
    """Return Meta App credentials for the given or active environment."""
    ICP = env["ir.config_parameter"].sudo()
    environment = environment or get_meta_environment(env)
    if environment not in ALL_ENVIRONMENTS:
        environment = ENV_TEST

    if environment == ENV_DEMO:
        return {
            "environment": ENV_DEMO,
            "app_id": "",
            "app_secret": "",
            "config_id": "",
            "is_demo": True,
        }

    prefix = _environment_prefix(environment)
    app_id = (ICP.get_param(f"mail_whatsapp.meta_{prefix}_app_id") or "").strip()
    app_secret = (
        ICP.get_param(f"mail_whatsapp.meta_{prefix}_app_secret") or ""
    ).strip()
    config_id = (
        ICP.get_param(f"mail_whatsapp.meta_{prefix}_embedded_signup_config_id")
        or ""
    ).strip()

    # Legacy single-app keys (pre environment switch).
    if not app_id:
        app_id = (ICP.get_param("mail_whatsapp.meta_app_id") or "").strip()
    if not app_secret:
        app_secret = (ICP.get_param("mail_whatsapp.meta_app_secret") or "").strip()
    if not config_id:
        config_id = (
            ICP.get_param("mail_whatsapp.embedded_signup_config_id") or ""
        ).strip()

    return {
        "environment": environment,
        "app_id": app_id,
        "app_secret": app_secret,
        "config_id": config_id,
        "is_demo": False,
    }


def get_all_meta_app_secrets(env):
    """Unique App Secrets from Test and Production (for signature checks)."""
    secrets = []
    for environment in (ENV_TEST, ENV_PRODUCTION):
        secret = get_meta_credentials(env, environment)["app_secret"]
        if secret and secret not in secrets:
            secrets.append(secret)
    return secrets


def sync_active_meta_credentials(env):
    """Mirror active environment credentials into legacy keys."""
    ICP = env["ir.config_parameter"].sudo()
    creds = get_meta_credentials(env)
    if creds.get("is_demo"):
        return creds
    ICP.set_param("mail_whatsapp.meta_app_id", creds["app_id"] or "")
    ICP.set_param("mail_whatsapp.meta_app_secret", creds["app_secret"] or "")
    ICP.set_param(
        "mail_whatsapp.embedded_signup_config_id", creds["config_id"] or ""
    )
    return creds


def migrate_legacy_meta_credentials(env):
    """Copy legacy single credentials into Test slots when empty."""
    ICP = env["ir.config_parameter"].sudo()
    legacy_app_id = (ICP.get_param("mail_whatsapp.meta_app_id") or "").strip()
    legacy_secret = (ICP.get_param("mail_whatsapp.meta_app_secret") or "").strip()
    legacy_config = (
        ICP.get_param("mail_whatsapp.embedded_signup_config_id") or ""
    ).strip()
    test_app_id = (ICP.get_param("mail_whatsapp.meta_test_app_id") or "").strip()
    if legacy_app_id and not test_app_id:
        ICP.set_param("mail_whatsapp.meta_test_app_id", legacy_app_id)
        _logger.info("Migrated legacy Meta App ID into Test credentials")
    if legacy_secret and not (
        ICP.get_param("mail_whatsapp.meta_test_app_secret") or ""
    ).strip():
        ICP.set_param("mail_whatsapp.meta_test_app_secret", legacy_secret)
    if legacy_config and not (
        ICP.get_param("mail_whatsapp.meta_test_embedded_signup_config_id") or ""
    ).strip():
        ICP.set_param(
            "mail_whatsapp.meta_test_embedded_signup_config_id", legacy_config
        )
    if not ICP.get_param(PARAM_ENVIRONMENT):
        ICP.set_param(PARAM_ENVIRONMENT, ENV_TEST)
