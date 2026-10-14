1. Register customer payments with the bank reference in **Memo**.
2. Import the bank statement file from the bank journal.
3. Lines whose reference and amount match a single open payment or invoice are
   reconciled automatically during the import.
4. Open the bank reconciliation of the journal to review the remaining lines;
   ambiguous matches are proposed there.

Lines imported before installing the module are processed by the scheduled
action *Try to reconcile automatically your statement lines*.
