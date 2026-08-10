Restrict confirmation of sale orders when free-to-use stock is insufficient.

The check uses real warehouse ``free_qty`` (with sudo) so stock-hiding
permissions cannot make the last available unit look like zero. Selling
exactly the available quantity is allowed (``free_qty == demand``).
