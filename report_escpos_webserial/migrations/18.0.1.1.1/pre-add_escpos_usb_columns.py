# -*- coding: utf-8 -*-


def _add_column_if_missing(cr, column, ddl):
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'ir_act_report_xml' AND column_name = %s
        """,
        (column,),
    )
    if not cr.fetchone():
        cr.execute(ddl)


def migrate(cr, version):
    _add_column_if_missing(
        cr,
        "escpos_transport",
        "ALTER TABLE ir_act_report_xml ADD COLUMN escpos_transport VARCHAR DEFAULT 'webserial'",
    )
    _add_column_if_missing(
        cr,
        "escpos_usb_vendor_id",
        "ALTER TABLE ir_act_report_xml ADD COLUMN escpos_usb_vendor_id INTEGER",
    )
    _add_column_if_missing(
        cr,
        "escpos_usb_product_id",
        "ALTER TABLE ir_act_report_xml ADD COLUMN escpos_usb_product_id INTEGER",
    )
