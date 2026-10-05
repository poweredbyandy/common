Makes the daily payments report of `l10n_ve_reports` use the **Process Date**
of `account_process_date` as the validation date.

The report looks for the date on the journal entry, then on its payment, and
falls back to the accounting date.
