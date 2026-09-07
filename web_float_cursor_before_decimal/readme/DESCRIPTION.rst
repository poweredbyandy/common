This module places the text cursor before the decimal separator when the
user focuses a float, monetary or percentage field.

With a value such as ``1,00``, the caret is set to ``1|,00`` instead of
``1,00|``. That lets the user type the integer part without appending
digits after the decimals.
