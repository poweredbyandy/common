In multi-device POS setups, cashiers often leave a draft order open on one
terminal and continue on another. Without persistence and locking, the previous
order may stay only on the first browser, or two devices can edit the same
shared draft at once and overwrite each other.

This module covers that business need: save the open order when switching or
locking the register, and prevent concurrent edition with a short renewable
lock that shows who is currently inside the order.
