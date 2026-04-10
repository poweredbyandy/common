{
    "name": "OAuth Provider",
    "summary": "OAuth servidor (flujo implícito) y validación de access_token para XML-RPC; respaldo IdP si auth_oauth está instalado.",
    "version": "18.0.1.1.4",
    "author": "andyengit",
    "maintainer": "andyengit",
    "category": "Technical",
    "license": "LGPL-3",
    "depends": ["web"],
    "data": [
        "security/ir.model.access.csv",
        "views/oauth_provider_views.xml",
    ],
    "installable": True,
    "application": False,
}
