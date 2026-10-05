import logging

from odoo.tools.sql import column_exists, rename_column

_logger = logging.getLogger(__name__)

_MODULE = "account_process_date"
_PREVIOUS_MODULE = "l10n_ve_seniat"
_FIELD = "l10n_ve_process_date"
_BACKUP_COLUMN = "l10n_ve_process_date_backup"
_TABLES = ("account_move", "account_payment")
_FIELD_XMLIDS = [
    f"field_{model}__{_FIELD}"
    for model in ("account_move", "account_bank_statement_line", "account_payment")
]


def _move_field_xmlids(cr):
    cr.execute(
        """
        UPDATE ir_model_data AS src
           SET module = %(module)s
         WHERE src.module = %(previous)s
           AND src.name = ANY(%(names)s)
           AND NOT EXISTS (
                SELECT 1
                  FROM ir_model_data AS dst
                 WHERE dst.module = %(module)s
                   AND dst.name = src.name
           )
        """,
        {"module": _MODULE, "previous": _PREVIOUS_MODULE, "names": _FIELD_XMLIDS},
    )
    return cr.rowcount


def _restore_backup_columns(cr):
    for table in _TABLES:
        if column_exists(cr, table, _BACKUP_COLUMN) and not column_exists(
            cr, table, _FIELD
        ):
            rename_column(cr, table, _BACKUP_COLUMN, _FIELD)
            _logger.info("Restored %s.%s from its backup column", table, _FIELD)


def pre_init_hook(env):
    moved = _move_field_xmlids(env.cr)
    if moved:
        _logger.info("Moved %s xmlids from %s to %s", moved, _PREVIOUS_MODULE, _MODULE)
    _restore_backup_columns(env.cr)
