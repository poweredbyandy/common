import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("""
        ALTER TABLE res_users
        ADD COLUMN IF NOT EXISTS commission_percent double precision DEFAULT 0.0
    """)
    cr.execute("""
        ALTER TABLE res_users
        ADD COLUMN IF NOT EXISTS commission_pending_invoice_count integer DEFAULT 0
    """)
    cr.execute("""
        ALTER TABLE res_users
        ADD COLUMN IF NOT EXISTS commission_pending_display varchar
    """)
    cr.execute("""
        ALTER TABLE res_users
        ADD COLUMN IF NOT EXISTS commission_billing_periodicity varchar DEFAULT 'daily'
    """)
    cr.execute("""
        ALTER TABLE res_users
        ADD COLUMN IF NOT EXISTS commission_billing_day integer DEFAULT 1
    """)
    _logger.info('pba_easy_commission: columnas de comision en res_users verificadas')
