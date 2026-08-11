In multi-device POS setups, cashiers often leave a draft order open on one
terminal and continue on another. Without a clear source of truth, each browser
may keep a stale local copy in IndexedDB and overwrite the server when it
reconnects.

This module treats PostgreSQL as the authoritative source for shared draft
orders. IndexedDB only keeps brand-new local orders that have not been synced
yet. Opening a shared order loads a canonical server snapshot under a short
renewable lock, and online edits are autosaved with confirmation before leaving
the order.
