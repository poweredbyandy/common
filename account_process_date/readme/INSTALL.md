Databases that already have process dates from `l10n_ve_seniat` keep them:

- Installed before upgrading `l10n_ve_seniat`, this module takes over the
  existing fields and their columns.
- Installed after the upgrade, it restores the columns that `l10n_ve_seniat`
  saved as `l10n_ve_process_date_backup`.
