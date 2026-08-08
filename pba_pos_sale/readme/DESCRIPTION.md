Allows creating a sales quotation (presupuesto) from the Point of Sale.

The cashier loads products in a POS order, presses **Generar Presupuesto**,
and the module creates a draft sale order with the same customer, products,
quantities, prices, discounts and taxes. The current POS order is then
deleted so the sale continues as a quotation in Sales.

Prices are converted from the POS currency to the pricelist currency of the
quotation (for example VES amounts in POS become USD on a USD pricelist).

The **Cotizaciones/Orden** button next to **Pedidos** in the navbar (and the
**Quotation/Order** action) lists sale orders whose currency matches any
available POS pricelist (not only the POS journal currency), so USD
quotations remain selectable when the register runs in VES.

When settling a quotation in another currency (for example USD), line amounts
are converted to the POS currency (VES) using the same exchange-rate logic as
generating a quotation the other way around. Selecting a quotation settles it
directly (no down-payment choice). The same sales order cannot be added twice
to one POS order.
