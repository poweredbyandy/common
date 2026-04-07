{
    'name': 'Odaura Theme Minimal',
    'description': 'A minimal theme for Odoo.',
    'category': 'Theme/Backend',
    'version': '18.0.1.0.0',
    'author': 'Odaura',
    'website': 'https://www.odaura.in',
    'license': 'OPL-1',
    'depends': ['web'],
        "images": [
        "static/description/banner.jpg",
        "static/description/theme_screenshot.jpg",
    ],
    'assets': {
        'web.assets_backend': [
            ('replace','web/static/src/scss/pre_variables.scss', 'odaura_theme_minimal/static/src/scss/pre_variables.scss'),
            ('replace','web/static/src/scss/primary_variables.scss', 'odaura_theme_minimal/static/src/scss/primary_variables.scss'),
            ('replace','web/static/src/scss/secondary_variables.scss', 'odaura_theme_minimal/static/src/scss/secondary_variables.scss'),
            'odaura_theme_minimal/static/src/scss/odaura_theme_buttons.scss',
        ],
    },
    'application': False,
    'installable': True,
    'auto_install': False,
    'summary': 'Minimal Odoo theme by Odaura',
}
