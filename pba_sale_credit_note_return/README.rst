======================================
PBA Devolucion desde nota de credito
======================================

Al confirmar una nota de credito de cliente vinculada a un pedido de venta,
el modulo crea automaticamente un albaran de devolucion del albaran original
con las cantidades de los productos de la nota de credito.

Al validar esa devolucion, la cantidad pedida de las lineas afectadas se
iguala a la cantidad entregada (0 si se devolvio todo), para que el pedido
no quede pendiente de entregar.

**Uso**

#. Entregue y facture el pedido de venta.
#. Cree y confirme la nota de credito sobre la factura (o desde el pedido).
#. Se genera un albaran de devolucion con los productos de la nota de credito.
#. Valide el albaran de devolucion cuando reciba la mercancia.
#. Las lineas del pedido actualizan la cantidad pedida a la cantidad entregada
   resultante (0 en una devolucion total).

**Contributors**

* andyengit
