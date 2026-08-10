{
    "name": "Res Users User",
    "version": "18.0.1.0.0",
    "category": "Hidden",
    "summary": (
        "Sub-users under a shared Odoo user for seller traceability, "
        "with PIN lock similar to POS cashier switch."
    ),
    "author": "andyengit",
    "maintainer": "andyengit",
    "website": "https://github.com/andyengit",
    "license": "LGPL-3",
    "depends": [
        "base",
        "web",
        "mail",
        "hr",
    ],
    "data": [
        "security/res_users_user_security.xml",
        "security/ir.model.access.csv",
        "views/res_users_user_views.xml",
        "views/res_users_views.xml",
        "views/hr_employee_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "res_users_user/static/src/scss/sub_user.scss",
            "res_users_user/static/src/js/sub_user_service.js",
            "res_users_user/static/src/js/sub_user_lock_screen.js",
            "res_users_user/static/src/xml/sub_user_lock_screen.xml",
            "res_users_user/static/src/js/sub_user_systray.js",
            "res_users_user/static/src/xml/sub_user_systray.xml",
            "res_users_user/static/src/js/message_patch.js",
        ],
    },
    "installable": True,
    "application": False,
}
