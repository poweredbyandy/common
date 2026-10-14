# Copyright 2026 andyengit
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Venezuela Bank Reconcile by Reference (Enterprise)",
    "summary": "Auto-match bank statement lines with payments by bank reference",
    "version": "18.0.1.0.0",
    "category": "Accounting/Accounting",
    "author": "andyengit",
    "maintainer": "andyengit",
    "website": "https://github.com/andyengit",
    "license": "LGPL-3",
    "depends": [
        "account_accountant",
        "account_statement_import_file",
    ],
    "data": [
        "data/account_reconcile_model_data.xml",
        "views/account_reconcile_model_views.xml",
    ],
    "installable": True,
    "application": False,
}
