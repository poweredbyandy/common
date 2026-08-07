Bridge module that extends `pba_pos_ux` product search in the Point of Sale so
cashiers can find products by internal code, including wildcard patterns with
`*`.

Loads the internal code field into the POS session and includes it in both the
local catalog filter and the server-side "search more" domain.
