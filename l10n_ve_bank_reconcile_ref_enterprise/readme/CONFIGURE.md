The module creates the reconciliation model **VE: Conciliar por referencia
bancaria** for the main company. It does not need a partner and it is
evaluated before the other models.

For other companies, or to tune it, go to **Accounting > Configuration >
Reconciliation Models** and set on an *Invoice Matching* rule:

- Match Invoice/bill with: **Reference** (and **Label** if your bank puts the
  reference there)
- **Match by bank reference**
- **Only match by bank reference**: recommended when the rule does not
  require a partner, so bank fees or transfers without a reference are not
  matched by amount
- **Suffix lengths**, for example `6,4`
- **Match payments before invoices**
- **Auto-validate**
