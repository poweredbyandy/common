{
    "name": "Account Process Date",
    "version": "18.0.1.0.0",
    "category": "Accounting/Accounting",
    "summary": "Track the date a journal entry or payment was actually processed",
    "author": "andyengit",
    "maintainer": "andyengit",
    "website": "https://github.com/andyengit",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [
        "views/account_move_views.xml",
        "views/account_payment_views.xml",
    ],
    "pre_init_hook": "pre_init_hook",
    "installable": True,
    "application": False,
}
