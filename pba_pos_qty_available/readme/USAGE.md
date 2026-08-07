1. Go to *Point of Sale ? Configuration ? Settings* (or open the POS config).
2. Enable **Show available quantity in catalog** for the terminal you want.
3. Close and reopen the POS session so products reload with stock data.
4. On the product screen, storable products show a badge with the free
   quantity. Colors indicate stock level; a muted style means the value comes
   from the offline cache.
5. Open POS terminals with the option enabled receive live updates when stock
   changes in Odoo (inventory adjustment, transfers, or sales on another
   register). Updates are pushed over the bus with quantities included, so
   registers do not poll the full catalog.
