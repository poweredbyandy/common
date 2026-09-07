In the backend, focusing a formatted number often leaves the caret at the
end of the input. Users then type after the decimals (``1,005``) instead of
extending the integer part (``15,00``).

This module restores the usual accounting entry behavior: on focus, the
caret sits immediately before the language decimal separator.
