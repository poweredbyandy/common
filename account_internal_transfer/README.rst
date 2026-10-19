==================
Internal Transfers
==================

Move money between bank and cash journals and exchange currencies at your own rate.

Confirming the document creates the outgoing payment and the incoming payment.
Both payments use the company liquidity transfer account, and those lines are
reconciled together. A currency exchange also posts the difference between the
company rate and the rate you enter.

**Table of contents**

.. contents::
   :local:

Use Cases / Context
===================

Treasury needs to move money between its own bank and cash journals without
going through a customer or a vendor. It also buys and sells foreign currency
at a rate that is not the rate stored in Odoo.

Each side of the operation has to stay a real payment, so it can be matched
with the bank statement of that journal. The gap between the company rate and
the agreed rate has to be posted on the exchange gain or loss accounts.

Configuration
=============

1. Go to **Accounting → Configuration → Settings**.
2. Set **Internal Transfer** to a current asset account that allows
   reconciliation and has no foreign currency.
3. For currency exchanges, set **Exchange Gain or Loss Journal**, **Gain
   Exchange Rate Account** and **Loss Exchange Rate Account**.

The currency of each journal decides the currency of its payment. Leave the
journal currency empty to use the company currency. A payment method that has
an outstanding account posts the payment on that account. Otherwise the
payment is posted on the journal's bank or cash account.

Usage
=====

1. Go to **Accounting → Accounting → Internal Transfers** and create a
   document.
2. Choose **Internal Transfer** to move an amount between two journals that
   share a currency. Set the source journal, its outgoing payment method
   and memo, the destination journal, its incoming payment method and memo,
   the date and the amount. The document memo is used on a payment that has
   no memo of its own.
3. Choose **Currency Exchange** when the journals use different currencies.
   Enter the amount that leaves and the custom rate (1 unit of the source
   currency = N units of the destination currency). You can also type the
   destination amount: the rate is recalculated.
4. The company-currency valuation shows the source at the company rate, the
   destination at your rate, and the difference. A positive difference is a
   gain.
5. Confirm. Odoo creates the outgoing payment, the incoming payment and, when
   the company-currency amounts differ, the exchange entry. The liquidity
   transfer account is reconciled.
6. Cancel from the transfer if you need to undo it. Reset to draft removes
   the canceled payments so the document can be confirmed again.

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/andyengit/common/issues>`_.
In case of trouble, please check there if your issue has already been reported.

Credits
=======

Authors
~~~~~~~

* andyengit

Maintainers
~~~~~~~~~~~

This module is maintained by andyengit.

Contributors
~~~~~~~~~~~~

* andyengit <anderson.armeya@gmail.com>
