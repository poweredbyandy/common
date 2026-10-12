{
    "name": "Account Move Change Journal",
    "version": "18.0.1.0.0",
    "category": "Accounting/Accounting",
    "summary": "Change the journal of posted customer and vendor invoices",
    "author": "andyengit",
    "maintainer": "andyengit",
    "maintainers": ["andyengit"],
    "website": "https://github.com/andyengit",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "wizards/account_move_change_journal_views.xml",
    ],
    "installable": True,
    "application": False,
}
