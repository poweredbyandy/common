#. Facture el pedido de venta (y entregalo si aplica).
#. Cree y confirme la nota de credito.
#. Si ya habia entrega validada: se genera un albaran de devolucion. Al
   validarlo, la cantidad pedida del pedido queda igual a la entregada
   (0 si se devolvio todo).
#. Si aun no habia entrega: se cancela/reduce el albaran pendiente y la
   cantidad pedida del pedido baja de inmediato (no se crea devolucion
   porque no hay stock en cliente).
