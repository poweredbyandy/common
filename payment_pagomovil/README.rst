==========
Pago Móvil
==========

Acepta pagos por pago móvil en el checkout.

El cliente ve el RIF, el teléfono y el banco donde debe enviar el dinero.
Luego informa el RIF o la cédula de origen, el teléfono, el banco desde
el que envió, la referencia bancaria y adjunta el comprobante. El pago
queda pendiente hasta que se confirma.

**Table of contents**

.. contents::
   :local:

Use Cases / Context
===================

El pago móvil no tiene una pasarela que confirme el cobro al momento.
Quien vende necesita los datos del envío y el comprobante para cotejarlos
con el banco antes de dar el pedido por pagado.

Configuration
=============

1. Instale el módulo **Pago Móvil**.
2. Vaya a **Contabilidad → Configuración → Proveedores de pago** (o
   **Sitio web → Configuración → Proveedores de pago**) y abra **Pago Móvil**.
3. Indique el titular, el RIF, el teléfono y el banco que reciben el pago.
4. Si usa contabilidad, elija el diario bancario donde se registrará el cobro.
5. Pase el proveedor a **Activado** y publíquelo.

El método solo se ofrece a clientes de Venezuela, o a clientes sin país.
Puede limitar las monedas del proveedor si el cobro es solo en bolívares.

Usage
=====

1. En el checkout, el cliente elige **Pago Móvil**.
2. Envía el monto al teléfono indicado.
3. Completa el RIF o la cédula de origen, el teléfono, el banco, la
   referencia y el comprobante (JPG, PNG, WEBP o PDF, hasta 5 MB).
4. El pedido queda con el pago pendiente.
5. En **Contabilidad → Proveedores de pago → Transacciones de pago**, abra
   la transacción, revise el comprobante y pulse **Confirmar pago** o
   **Rechazar**.

Al confirmar, se valida el pedido y se crea el pago. La misma referencia
bancaria no puede usarse dos veces con el mismo teléfono, salvo que el
intento anterior se haya rechazado.

Contributors
============

* andyengit <anderson.armeya@gmail.com>
