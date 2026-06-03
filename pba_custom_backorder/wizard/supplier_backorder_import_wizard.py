import base64
import hashlib
import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .backorder_excel_parser import BackorderExcelParser


class PbaSupplierBackorderImportWizard(models.TransientModel):
    _name = "pba.supplier.backorder.import.wizard"
    _inherit = "pba.backorder.product.match.mixin"
    _description = "Importar backorder de proveedor desde Excel"

    state = fields.Selection(
        selection=[
            ("upload", "1. Archivo"),
            ("mapping", "2. Autoconfiguración"),
            ("review", "3. Revisión"),
        ],
        default="upload",
        required=True,
    )
    file_data = fields.Binary(string="Archivo Excel", attachment=False)
    file_name = fields.Char(string="Nombre de archivo")
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    header_row = fields.Integer(
        string="Fila de encabezados",
        default=1,
        help="Número de fila (1-based) donde están los títulos de columna.",
    )
    sheet_name = fields.Char(string="Hoja activa", readonly=True)
    sheet_index = fields.Integer(
        string="Número de hoja",
        default=0,
        help="0 = primera hoja. En archivos con varias pestañas (p. ej. KP, KGK), elija la hoja a importar.",
    )
    available_sheet_names = fields.Text(
        string="Hojas del archivo",
        readonly=True,
    )
    detected_headers = fields.Text(string="Columnas detectadas", readonly=True)
    column_mapping_json = fields.Text(string="Mapeo de columnas (JSON)")
    col_item = fields.Char(string="Columna ítem")
    col_internal_code = fields.Char(
        string="Columna Nº parte / código interno",
        required=False,
    )
    col_product_ref = fields.Char(string="Columna referencia")
    col_description = fields.Char(string="Columna descripción")
    col_supplier_name = fields.Char(string="Columna proveedor (archivo)")
    col_factory = fields.Char(string="Columna fábrica")
    col_order_ref = fields.Char(string="Columna Nº pedido")
    col_confirmation = fields.Char(string="Columna confirmación")
    col_quantity = fields.Char(string="Columna cantidad")
    col_uom = fields.Char(string="Columna unidad")
    col_unit_price = fields.Char(string="Columna precio unitario")
    col_line_total = fields.Char(string="Columna total")
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Moneda",
    )
    currency_detected = fields.Boolean(
        string="Moneda detectada automáticamente",
        readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Proveedor",
        domain="[('supplier_rank', '>', 0)]",
    )
    confirmation_ref = fields.Char(string="Referencia / confirmación")
    factory_name = fields.Char(string="Fábrica (archivo)")
    line_ids = fields.One2many(
        comodel_name="pba.supplier.backorder.import.line",
        inverse_name="wizard_id",
        string="Líneas",
    )
    missing_product_count = fields.Integer(
        compute="_compute_line_stats",
    )
    ready_line_count = fields.Integer(
        compute="_compute_line_stats",
    )
    total_line_count = fields.Integer(
        compute="_compute_line_stats",
    )
    purchase_order_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Orden de compra creada",
        readonly=True,
    )
    file_hash = fields.Char(string="Hash del archivo", readonly=True)
    existing_purchase_order_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Orden de compra existente",
        readonly=True,
    )
    confirmation_collision_order_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Orden con misma confirmación",
        readonly=True,
    )
    duplicate_warning = fields.Html(
        compute="_compute_duplicate_warning",
        sanitize=False,
    )
    import_mode = fields.Selection(
        selection=[
            ("create", "Crear nueva orden"),
            ("update", "Actualizar orden existente"),
            ("open", "Abrir orden existente"),
        ],
        string="Acción",
        default="create",
        readonly=True,
    )
    preview_html = fields.Html(compute="_compute_preview_html", sanitize=False)

    @api.depends("line_ids", "line_ids.product_match")
    def _compute_line_stats(self):
        for wizard in self:
            lines = wizard.line_ids
            wizard.total_line_count = len(lines)
            wizard.missing_product_count = len(
                lines.filtered(lambda l: l.product_match == "missing")
            )
            wizard.ready_line_count = len(
                lines.filtered(
                    lambda l: l.product_match in ("matched", "created")
                    and l.product_id
                )
            )

    @api.depends(
        "existing_purchase_order_id",
        "existing_purchase_order_id.state",
        "confirmation_collision_order_id",
        "confirmation_ref",
        "file_hash",
        "partner_id",
    )
    def _compute_duplicate_warning(self):
        for wizard in self:
            collision = wizard.confirmation_collision_order_id
            if collision and not wizard.existing_purchase_order_id:
                state_label = dict(collision._fields["state"].selection).get(
                    collision.state, collision.state
                )
                wizard.duplicate_warning = (
                    "<div class='alert alert-warning' role='alert'>"
                    "<p><b>Misma referencia, otro archivo.</b> La confirmación "
                    "<b>%s</b> ya está en la orden <b>%s</b> (%s), importada "
                    "desde otro Excel.</p>"
                    "<p>Se creará una <b>nueva</b> orden para este archivo. "
                    "Si desea actualizar la anterior, cambie la referencia "
                    "de confirmación o reimporte el mismo archivo.</p></div>"
                ) % (
                    wizard.confirmation_ref or collision.pba_backorder_confirmation,
                    collision.name,
                    state_label,
                )
                continue
            po = wizard.existing_purchase_order_id
            if not po:
                wizard.duplicate_warning = False
                continue
            state_label = dict(po._fields["state"].selection).get(po.state, po.state)
            ref = wizard.confirmation_ref or po.pba_backorder_confirmation
            if po.state in ("purchase", "done"):
                wizard.duplicate_warning = (
                    "<div class='alert alert-warning' role='alert'>"
                    "<p><b>Backorder ya importado.</b> La confirmación "
                    "<b>%s</b> ya tiene la orden <b>%s</b> (%s).</p>"
                    "<p>No se creará información duplicada. Puede abrir la orden existente."
                    "</p></div>"
                ) % (ref, po.name, state_label)
            else:
                wizard.duplicate_warning = (
                    "<div class='alert alert-info' role='alert'>"
                    "<p><b>Backorder ya registrado.</b> La confirmación "
                    "<b>%s</b> corresponde a la orden <b>%s</b> (%s).</p>"
                    "<p>Al importar de nuevo se actualizarán cantidades y precios "
                    "sin duplicar líneas.</p></div>"
                ) % (ref, po.name, state_label)

    @api.depends(
        "col_internal_code",
        "col_quantity",
        "col_unit_price",
        "detected_headers",
    )
    def _compute_preview_html(self):
        for wizard in self:
            parts = []
            if wizard.col_internal_code:
                parts.append(
                    "<li><b>Nº parte / código interno:</b> %s</li>"
                    % wizard.col_internal_code
                )
            if wizard.col_description:
                parts.append(
                    "<li><b>Descripción:</b> %s</li>" % wizard.col_description
                )
            if wizard.col_quantity:
                parts.append("<li><b>Cantidad:</b> %s</li>" % wizard.col_quantity)
            if wizard.col_unit_price:
                parts.append(
                    "<li><b>Precio:</b> %s</li>" % wizard.col_unit_price
                )
            if wizard.currency_id:
                parts.append(
                    "<li><b>Moneda:</b> %s</li>" % wizard.currency_id.display_name
                )
            wizard.preview_html = (
                "<ul>%s</ul>" % "".join(parts) if parts else False
            )

    def _headers_list(self):
        self.ensure_one()
        if not self.detected_headers:
            return []
        return [h for h in self.detected_headers.split("\n") if h]

    def _parser_kwargs(self):
        self.ensure_one()
        return {
            "filename": self.file_name,
            "sheet_index": self.sheet_index or 0,
        }

    def _allowed_extensions(self):
        return (".xlsx", ".xlsm", ".xls")

    def _check_file_extension(self):
        self.ensure_one()
        if self.file_name and not self.file_name.lower().endswith(self._allowed_extensions()):
            raise UserError(
                _("Solo se admiten archivos Excel (.xlsx, .xlsm, .xls).")
            )

    def _build_mapping_json_from_fields(self):
        self.ensure_one()
        mapping = {}
        field_map = {
            "item": self.col_item,
            "internal_code": self.col_internal_code,
            "product_ref": self.col_product_ref,
            "description": self.col_description,
            "supplier_name": self.col_supplier_name,
            "factory": self.col_factory,
            "order_ref": self.col_order_ref,
            "confirmation": self.col_confirmation,
            "quantity": self.col_quantity,
            "uom": self.col_uom,
            "unit_price": self.col_unit_price,
            "line_total": self.col_line_total,
        }
        for key, col_name in field_map.items():
            if col_name:
                mapping[key] = col_name
        return mapping

    def _get_column_mapping(self):
        self.ensure_one()
        headers = self._headers_list()
        mapping_json = self.column_mapping_json
        if mapping_json:
            try:
                data = json.loads(mapping_json)
            except json.JSONDecodeError as err:
                raise UserError(_("Mapeo de columnas inválido.")) from err
        else:
            data = self._build_mapping_json_from_fields()
        column_mapping = BackorderExcelParser.json_to_column_mapping(data, headers)
        if "internal_code" not in column_mapping:
            raise UserError(
                _("Debe mapear la columna de número de parte / código interno.")
            )
        return column_mapping

    def _resolve_currency(self, currency_code):
        if not currency_code:
            return self.env["res.currency"], False
        currency = self.env["res.currency"].search(
            [("name", "=", currency_code.upper())],
            limit=1,
        )
        return currency, bool(currency)

    def _resolve_uom(self, uom_name):
        Uom = self.env["uom.uom"]
        if not uom_name:
            return self.env.ref("uom.product_uom_unit")
        name = uom_name.strip().upper().replace(".", "")
        aliases = {
            "PZS": "Units",
            "PCS": "Units",
            "PC": "Units",
            "SETS": "Units",
            "SET": "Units",
            "JGOS": "Units",
            "JGO": "Units",
            "UN": "Units",
            "UNI": "Units",
        }
        search_name = aliases.get(name, uom_name)
        uom = Uom.search([("name", "ilike", search_name)], limit=1)
        return uom or self.env.ref("uom.product_uom_unit")

    def _compute_file_hash(self):
        self.ensure_one()
        if not self.file_data:
            return False
        raw = base64.b64decode(self.file_data)
        if not raw:
            return False
        return hashlib.sha256(raw).hexdigest()

    def _get_backorder_identity(self):
        self.ensure_one()
        return self.env["purchase.order"]._pba_normalize_confirmation(
            self.confirmation_ref
        )

    def _find_existing_purchase_order(self):
        self.ensure_one()
        PurchaseOrder = self.env["purchase.order"]
        file_hash = self.file_hash or self._compute_file_hash()
        confirmation = self._get_backorder_identity()
        return PurchaseOrder._pba_find_supplier_backorder(
            confirmation,
            company_id=self.company_id.id,
            file_hash=file_hash,
        )

    def _resolve_backorder_match(self):
        self.ensure_one()
        PurchaseOrder = self.env["purchase.order"]
        file_hash = self.file_hash or self._compute_file_hash()
        confirmation = self._get_backorder_identity()
        po_by_hash = PurchaseOrder._pba_find_by_file_hash(
            file_hash, company_id=self.company_id.id
        )
        po_by_conf = PurchaseOrder._pba_find_by_confirmation(
            confirmation, company_id=self.company_id.id
        )
        if po_by_hash:
            return po_by_hash, False
        if po_by_conf:
            stored_hash = po_by_conf.pba_backorder_file_hash
            if not stored_hash or stored_hash == file_hash:
                return po_by_conf, False
            return PurchaseOrder.browse(), po_by_conf
        return PurchaseOrder.browse(), False

    def _refresh_existing_purchase_detection(self):
        self.ensure_one()
        file_hash = self._compute_file_hash()
        po, collision_po = self._resolve_backorder_match()
        if po:
            import_mode = (
                "open" if po.state in ("purchase", "done") else "update"
            )
        else:
            import_mode = "create"
        vals = {
            "file_hash": file_hash,
            "existing_purchase_order_id": po.id if po else False,
            "confirmation_collision_order_id": collision_po.id if collision_po else False,
            "import_mode": import_mode,
        }
        if po and not self.partner_id:
            vals["partner_id"] = po.partner_id.id
        self.write(vals)

    def _apply_auto_config(self, config):
        self.ensure_one()
        headers = config["headers"]
        mapping = config["column_mapping"]
        mapping_json = BackorderExcelParser.mapping_to_json(mapping, headers)
        sheet_names = config.get("sheet_names") or []
        field_vals = {
            "header_row": config["header_row"],
            "sheet_name": config.get("sheet_name") or "",
            "sheet_index": config.get("sheet_index", self.sheet_index or 0),
            "available_sheet_names": "\n".join(
                "%s: %s" % (idx, name) for idx, name in enumerate(sheet_names)
            )
            if sheet_names
            else "",
            "detected_headers": "\n".join(h for h in headers if h),
            "column_mapping_json": json.dumps(mapping_json, ensure_ascii=False),
            "col_item": mapping_json.get("item", ""),
            "col_internal_code": mapping_json.get("internal_code")
            or mapping_json.get("part_number", ""),
            "col_product_ref": mapping_json.get("product_ref", ""),
            "col_description": mapping_json.get("description", ""),
            "col_supplier_name": mapping_json.get("supplier_name", ""),
            "col_factory": mapping_json.get("factory", ""),
            "col_order_ref": mapping_json.get("order_ref", ""),
            "col_confirmation": mapping_json.get("confirmation", ""),
            "col_quantity": mapping_json.get("quantity", ""),
            "col_uom": mapping_json.get("uom", ""),
            "col_unit_price": mapping_json.get("unit_price", ""),
            "col_line_total": mapping_json.get("line_total", ""),
            "confirmation_ref": config.get("confirmation_ref") or "",
        }
        currency, detected = self._resolve_currency(config.get("currency_code"))
        if currency:
            field_vals["currency_id"] = currency.id
            field_vals["currency_detected"] = detected
        else:
            field_vals["currency_detected"] = False
        if mapping_json.get("factory") and not field_vals.get("factory_name"):
            factories = set()
            column_mapping = mapping
            for row in BackorderExcelParser.iter_data_rows(
                self.file_data,
                config["header_row"],
                column_mapping,
                **self._parser_kwargs(),
            ):
                if row.get("factory"):
                    factories.add(row["factory"])
            if len(factories) == 1:
                field_vals["factory_name"] = next(iter(factories))
        field_vals["file_hash"] = self._compute_file_hash()
        self.write(field_vals)
        self._refresh_existing_purchase_detection()

    def action_analyze_file(self):
        self.ensure_one()
        if not self.file_data:
            raise UserError(_("Seleccione un archivo Excel."))
        self._check_file_extension()
        config = BackorderExcelParser.auto_configure(
            self.file_data,
            filename=self.file_name,
            sheet_index=None,
        )
        self._apply_auto_config(config)
        self.state = "mapping"
        return self._reopen_wizard()

    def action_apply_sheet(self):
        self.ensure_one()
        if not self.file_data:
            raise UserError(_("No hay archivo cargado."))
        config = BackorderExcelParser.auto_configure(
            self.file_data,
            filename=self.file_name,
            sheet_index=self.sheet_index or 0,
        )
        self._apply_auto_config(config)
        return self._reopen_wizard()

    def action_reanalyze(self):
        self.ensure_one()
        if not self.file_data:
            raise UserError(_("No hay archivo cargado."))
        config = BackorderExcelParser.auto_configure(
            self.file_data,
            filename=self.file_name,
            sheet_index=self.sheet_index or 0,
        )
        headers = self._headers_list()
        manual = self._build_mapping_json_from_fields()
        auto_json = BackorderExcelParser.mapping_to_json(
            config["column_mapping"], config["headers"]
        )
        for key, val in manual.items():
            if val:
                auto_json[key] = val
        config["column_mapping"] = BackorderExcelParser.json_to_column_mapping(
            auto_json, headers or config["headers"]
        )
        self._apply_auto_config(config)
        return self._reopen_wizard()

    def action_go_to_review(self):
        self.ensure_one()
        if not self.col_internal_code:
            raise UserError(
                _("Indique la columna de número de parte / código interno.")
            )
        column_mapping = self._get_column_mapping()
        mapping_json = self._build_mapping_json_from_fields()
        self.column_mapping_json = json.dumps(mapping_json, ensure_ascii=False)
        self.line_ids.unlink()
        line_vals = []
        seq = 10
        factories = set()
        confirmations = set()
        for row in BackorderExcelParser.iter_data_rows(
            self.file_data,
            self.header_row,
            column_mapping,
            **self._parser_kwargs(),
        ):
            product = self._find_product_for_backorder_row(row)
            uom = self._resolve_uom(row.get("uom_name"))
            if row.get("factory"):
                factories.add(row["factory"])
            if row.get("confirmation"):
                confirmations.add(row["confirmation"])
            line_vals.append(
                (
                    0,
                    0,
                    {
                        "sequence": seq,
                        "internal_code": row.get("internal_code") or "",
                        "product_ref": row.get("product_ref") or "",
                        "description": row.get("description"),
                        "supplier_name": row.get("supplier_name"),
                        "factory": row.get("factory"),
                        "order_ref": row.get("order_ref"),
                        "confirmation": row.get("confirmation"),
                        "quantity": row.get("quantity") or 0.0,
                        "uom_name": row.get("uom_name"),
                        "unit_price": row.get("unit_price") or 0.0,
                        "line_total": row.get("line_total") or 0.0,
                        "product_id": product.id if product else False,
                        "product_match": "matched" if product else "missing",
                        "uom_id": uom.id,
                    },
                )
            )
            seq += 10
        if not line_vals:
            raise UserError(_("No se encontraron líneas de producto en el archivo."))
        vals = {"line_ids": line_vals, "state": "review"}
        if not self.confirmation_ref and len(confirmations) == 1:
            vals["confirmation_ref"] = next(iter(confirmations))
        if not self.factory_name and len(factories) == 1:
            vals["factory_name"] = next(iter(factories))
        self.write(vals)
        self._refresh_existing_purchase_detection()
        return self._reopen_wizard()

    @api.onchange("partner_id", "confirmation_ref")
    def _onchange_partner_confirmation(self):
        if self.state == "review" and (self.confirmation_ref or self.file_hash):
            self._refresh_existing_purchase_detection()

    def _get_importable_lines(self):
        self.ensure_one()
        return self.line_ids.filtered(
            lambda l: l.product_match != "skipped" and l.product_id
        )

    def _prepare_purchase_order_line_vals(self, line):
        return {
            "product_id": line.product_id.id,
            "name": line.description or line.product_id.display_name,
            "product_qty": line.quantity,
            "product_uom": line.uom_id.id or line.product_id.uom_po_id.id,
            "price_unit": line.unit_price,
            "date_planned": fields.Datetime.now(),
        }

    def _sync_purchase_order_lines(self, purchase, lines):
        existing_by_product = {
            pol.product_id.id: pol
            for pol in purchase.order_line
            if pol.product_id and not pol.display_type
        }
        for line in lines:
            vals = self._prepare_purchase_order_line_vals(line)
            pol = existing_by_product.get(line.product_id.id)
            if pol:
                pol.write(vals)
            else:
                self.env["purchase.order.line"].create(
                    {"order_id": purchase.id, **vals}
                )

    def _update_purchase_order_metadata(self, purchase):
        self.ensure_one()
        purchase.write(
            {
                "partner_id": self.partner_id.id,
                "currency_id": self.currency_id.id,
                "pba_backorder_factory": self.factory_name or False,
                "pba_backorder_import_filename": self.file_name or False,
                "pba_backorder_file_hash": self.file_hash or self._compute_file_hash(),
                "pba_backorder_confirmation": self._get_backorder_identity()
                or purchase.pba_backorder_confirmation,
                "partner_ref": self._get_backorder_identity() or purchase.partner_ref,
            }
        )

    def action_create_purchase_order(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("Seleccione el proveedor de la compra."))
        if not self.currency_id:
            raise UserError(_("Seleccione la moneda del backorder."))
        if not self._get_backorder_identity() and not (self.file_hash or self._compute_file_hash()):
            raise UserError(
                _(
                    "No se pudo identificar el backorder. "
                    "Indique la referencia de confirmación o use un archivo válido."
                )
            )
        self._refresh_existing_purchase_detection()
        lines = self._get_importable_lines()
        if not lines:
            raise UserError(
                _(
                    "No hay líneas listas para importar. "
                    "Cree o vincule los productos faltantes u omita líneas."
                )
            )
        missing = self.line_ids.filtered(
            lambda l: l.product_match == "missing"
        )
        if missing:
            raise UserError(
                _(
                    "Quedan %(count)s líneas sin producto. "
                    "Créelos, vincúlelos u omítalos antes de importar.",
                    count=len(missing),
                )
            )
        existing = self.existing_purchase_order_id
        if existing and self.import_mode == "open":
            self.purchase_order_id = existing.id
            return self._action_open_purchase_order(existing)

        if existing and self.import_mode == "update":
            if existing.state in ("purchase", "done"):
                raise UserError(
                    _(
                        "La orden %(name)s ya está confirmada. "
                        "No se puede actualizar para evitar duplicar información.",
                        name=existing.name,
                    )
                )
            self._sync_purchase_order_lines(existing, lines)
            self._update_purchase_order_metadata(existing)
            self.purchase_order_id = existing.id
            return self._action_open_purchase_order(
                existing,
                notification=_(
                    "Se actualizó la orden %(name)s sin duplicar líneas.",
                    name=existing.name,
                ),
            )

        po_name = self._get_backorder_identity() or self.file_name or _("Backorder")
        order_lines = [
            (0, 0, self._prepare_purchase_order_line_vals(line)) for line in lines
        ]
        po_vals = {
            "partner_id": self.partner_id.id,
            "currency_id": self.currency_id.id,
            "company_id": self.company_id.id,
            "origin": _("Backorder: %s", po_name),
            "partner_ref": self._get_backorder_identity() or False,
            "order_line": order_lines,
            "pba_is_supplier_backorder": True,
            "pba_backorder_confirmation": self._get_backorder_identity(),
            "pba_backorder_factory": self.factory_name or False,
            "pba_backorder_import_filename": self.file_name or False,
            "pba_backorder_file_hash": self.file_hash or self._compute_file_hash(),
        }
        purchase = self.env["purchase.order"].create(po_vals)
        self.purchase_order_id = purchase.id
        return self._action_open_purchase_order(purchase)

    def _action_open_purchase_order(self, purchase, notification=None):
        action = {
            "type": "ir.actions.act_window",
            "name": _("Orden de compra (backorder)"),
            "res_model": "purchase.order",
            "view_mode": "form",
            "res_id": purchase.id,
            "target": "current",
        }
        if notification:
            action["context"] = dict(
                self.env.context,
                default_notification=notification,
            )
        return action

    def action_back_to_upload(self):
        self.write({"state": "upload"})
        return self._reopen_wizard()

    def action_back_to_mapping(self):
        self.write({"state": "mapping"})
        return self._reopen_wizard()

    def _reopen_wizard(self):
        return self.get_reopen_form_action()

    def get_reopen_form_action(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Importar backorder de proveedor"),
            "res_model": self._name,
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }
