Al confirmar una nota de crédito de cliente vinculada a un pedido de venta,
el módulo crea automáticamente un albarán de devolución del albarán original
con las cantidades de los productos de la nota de crédito.

Al validar esa devolución, la cantidad pedida de las líneas afectadas se
iguala a la cantidad entregada (0 si se devolvió todo), para que el pedido
no quede pendiente de entregar.
