1. Install the module (`point_of_sale` is required).
2. Create or select a Point of Sale for sellers.
3. Open **Point of Sale ? Configuration ? Settings**, select that POS and
   enable **Seller Register**. Save.
4. Open the Seller Register session (it opens without cash control and cannot
   be closed from the POS menu).
5. You can keep changing seller POS settings while that session stays open.
6. Optionally enable **Share Open Orders** between cashier and seller POS so
   both can see the same draft orders while working.
7. Cashiers work and close their own POS as usual:
   - Draft orders with products move automatically to the open Seller Register.
   - Empty carts are discarded.
   - Sellers can keep working without leaving their POS.
8. If the Seller Register is not open when a cashier tries to close, Odoo asks
   to open it first; draft orders are not cancelled.
