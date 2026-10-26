La cola es del módulo. No usa la cola de trabajos.

El botón guarda las líneas pendientes. El cron del módulo procesa 100
líneas o 30 segundos y, si quedan líneas, programa la tanda siguiente.
Si la cola está vacía, el cron no concilia nada.

Cada línea encolada se concilia así: si la etiqueta contiene COMISION,
el monto completo va a la cuenta de gasto configurada, sin crear un
pago. Si no, se busca el movimiento por número de referencia y, si no
hay uno solo, un cierre de punto de venta ya publicado con la misma
fecha de abono y el mismo monto.
