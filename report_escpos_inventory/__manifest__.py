{
    "name": "Inventario ESC/POS",
    "version": "18.0.1.30.2",
    "category": "Inventory",
    "summary": "Informes ESC/POS o ESC/P Epson matriz para stock (nota de despacho, etc.)",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": [
        "sale_stock",
        "sale_stock_picking_invoice_link",
        "report_escpos_webserial",
        "product_brand",
        "pba_internal_code",
    ],
    "data": [
        "data/report_stock_picking_dispatch_escpos.xml",
        "data/report_stock_picking_dispatch_pdf.xml",
        "data/report_stock_picking_escp_test.xml",
    ],
    "installable": True,
    "application": False,
}
