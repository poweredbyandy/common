Este módulo sincroniza entre compañías todos los campos de contacto configurables por compañía (`company_dependent`) detectados dinámicamente en ``res.partner``.

Al editar un contacto en cualquier compañía, los valores compatibles se replican automáticamente en las demás compañías. También incluye un asistente para copiar manualmente la configuración de una compañía origen hacia una o varias compañías destino.

Si otro módulo agrega nuevos campos ``company_dependent`` al contacto, este módulo los incluirá automáticamente sin necesidad de modificaciones.

Las referencias solo se copian si el registro existe o es válido en la compañía destino. Si un valor pertenece exclusivamente a otra compañía, ese campo no se modifica en la compañía destino.
