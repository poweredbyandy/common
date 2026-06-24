# Powered By Andy - SaaS Enterprise

Módulo integrador que instala los módulos base necesarios para el SaaS de Venezuela en **Odoo 18.0 Enterprise**.

Es la variante Enterprise de `poweredbyandy_saas`. Excluye módulos incompatibles con Enterprise o que tienen equivalencia nativa en Odoo Enterprise.

## Diferencias con `poweredbyandy_saas`

### Excluidos (incompatibles o con equivalente Enterprise)

| Módulo | Motivo |
|--------|--------|
| `web_responsive` | `excludes: web_enterprise` |
| `web_dark_mode` | `excludes: web_enterprise` |
| `account_reconcile_oca` | Equivalente: `account_accountant` |
| `account_reconcile_model_oca` | `excludes: account_accountant` |
| `account_in_payment` | Depende de `account_reconcile_oca` |
| `account_partner_reconcile` | Depende de `account_reconcile_oca` |
| `account_statement_import_file_reconcile_oca` | Depende de `account_reconcile_oca` |

### Incluidos adicionalmente

| Módulo | Motivo |
|--------|--------|
| `account_accountant` | Conciliación bancaria nativa de Enterprise |

### Notas

- `l10n_ve_seniat` se incluye aunque excluye Studio (`web_studio`, `studio_customization`); funciona en Enterprise sin Studio.
- Incluye watermark en el Home Menu de Enterprise (`web_enterprise.HomeMenu`).
- La importación de extractos bancarios usa los módulos OCA (`account_statement_import_*`) más `l10n_ve_bank_statement_import`, compatibles con Enterprise.

## Instalación

Requiere Odoo 18.0 **Enterprise** con los mismos repositorios OCA que `poweredbyandy_saas`, excepto `OCA/account-reconcile` (ya no es necesario).

Instalar el módulo `poweredbyandy_e_saas` en lugar de `poweredbyandy_saas`.
