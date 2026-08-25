import base64
import logging
from datetime import datetime

from odoo import api, fields, models, _
from odoo.tools.misc import format_date

_logger = logging.getLogger(__name__)

POS80_DEVICE_CODE = "pos80"
POS80_PRINT_NOTIFICATION = "pba.stock.picking/print_pos80"
LINE_WIDTH = 48


def _encode(text):
    return (text or "").encode("cp1252", "replace")


def _clip(text, width=LINE_WIDTH):
    return (text or "")[:width]


def _center(text, width=LINE_WIDTH):
    value = _clip(text, width)
    return value.center(width)


def _row(left, right="", width=LINE_WIDTH):
    left = (left or "")[:width]
    right = (right or "")[:width]
    if not right:
        return left
    pad = width - len(left) - len(right)
    if pad < 1:
        return _clip("%s %s" % (left, right), width)
    return left + (" " * pad) + right


LOCATION_PREFIX = "---> "
QTY_WIDTH = 3
NAME_INDENT = 7


def _qty_label(qty):
    if qty == int(qty):
        return str(int(qty))
    return ("%.2f" % qty).rstrip("0").rstrip(".")


def _qty_cell(qty):
    label = _qty_label(qty)
    if len(label) < QTY_WIDTH:
        label = label.rjust(QTY_WIDTH)
    return "%sx" % label


def _wrap(text, width=LINE_WIDTH):
    words = (text or "").split()
    if not words:
        return [""]
    lines = []
    current = words[0]
    for word in words[1:]:
        candidate = "%s %s" % (current, word)
        if len(candidate) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    chunks = []
    for line in lines:
        remain = line
        while len(remain) > width:
            chunks.append(remain[:width])
            remain = remain[width:]
        if remain:
            chunks.append(remain)
    return chunks or [""]


def _split_first_line(text, width):
    value = text or ""
    if len(value) <= width:
        return value, ""
    head = value[:width]
    cut = head.rfind(" ")
    if cut < 1:
        cut = head.rfind("/")
    if cut < 1:
        cut = width
    return value[:cut], value[cut:].lstrip(" /")


class StockPicking(models.Model):
    _inherit = "stock.picking"

    pba_pos80_auto_printed = fields.Boolean(copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        pickings = super().create(vals_list)
        pickings.filtered("move_ids")._pba_pos80_autoprint()
        return pickings

    def action_print_pos80(self):
        self._pba_pos80_ensure_device()
        return {
            "type": "ir.actions.client",
            "tag": "pba_printer_delivery_print",
            "name": _("Print POS-80"),
            "params": {"picking_ids": self.ids},
        }

    @api.model
    def get_pos80_print_payload(self, picking_ids):
        self._pba_pos80_ensure_device()
        pickings = self.browse(picking_ids).exists()
        return [picking._pba_pos80_ticket_payload() for picking in pickings]

    def _pba_pos80_autoprint(self):
        if self.env.context.get("install_mode"):
            return
        pickings = self.filtered(lambda picking: picking._pba_pos80_should_autoprint())
        if not pickings:
            return
        pickings.pba_pos80_auto_printed = True
        for picking in pickings:
            try:
                with self.env.cr.savepoint():
                    payload = picking._pba_pos80_ticket_payload()
                    if picking._pba_pos80_try_gateway_print(payload):
                        continue
                    picking._pba_pos80_notify_local_print(payload)
            except Exception:
                _logger.exception(
                    "POS-80 auto-print failed for picking %s",
                    picking.id,
                )

    def _pba_pos80_should_autoprint(self):
        self.ensure_one()
        if self.pba_pos80_auto_printed:
            return False
        if self.picking_type_code != "outgoing":
            return False
        if not self.move_ids.filtered(lambda move: move.state != "cancel"):
            return False
        return bool(self.company_id.pba_pos80_auto_print)

    def _pba_pos80_ensure_device(self):
        from odoo.addons.pba_printer_delivery.hooks import _ensure_pos80_device

        try:
            with self.env.cr.savepoint():
                _ensure_pos80_device(self.env)
        except Exception:
            _logger.debug("POS-80 device ensure skipped", exc_info=True)

    def _pba_pos80_printer_codes(self):
        report = self.env.ref(
            "pba_printer_delivery.action_report_stock_picking_pos80",
            raise_if_not_found=False,
        )
        if report and "device_bridge_ids" in report._fields:
            codes = report.device_bridge_ids.filtered("active").mapped("code")
            if codes:
                return codes
        return [POS80_DEVICE_CODE]

    def _pba_pos80_try_gateway_print(self, payload):
        if "device.bridge.gateway" not in self.env:
            return False
        self._pba_pos80_ensure_device()
        codes = payload.get("device_codes") or [payload["device_code"]]
        for code in codes:
            try:
                with self.env.cr.savepoint():
                    self.env["device.bridge.gateway"].send_raw_job(
                        code,
                        payload["data_b64"],
                    )
                return True
            except Exception:
                _logger.debug("POS-80 gateway print skipped", exc_info=True)
        return False

    def _pba_pos80_notify_user(self):
        if "device.bridge.gateway" in self.env:
            Gateway = self.env["device.bridge.gateway"]
            codes = self._pba_pos80_printer_codes()
            devices = self.env["device.bridge"].sudo().search(
                [("code", "in", codes), ("active", "=", True)]
            )
            gateway = Gateway.sudo().search(
                [("device_id", "in", devices.ids)] + Gateway._online_domain(),
                order="last_seen desc",
                limit=1,
            )
            if gateway:
                return gateway.user_id
        return self.env.user

    def _pba_pos80_notify_local_print(self, payload):
        self._pba_pos80_notify_user()._bus_send(POS80_PRINT_NOTIFICATION, payload)

    def _pba_pos80_ticket_payload(self):
        self.ensure_one()
        raw = self._pba_pos80_ticket_bytes()
        codes = self._pba_pos80_printer_codes()
        return {
            "picking_id": self.id,
            "name": self.name,
            "device_code": codes[0],
            "device_codes": codes,
            "data_b64": base64.b64encode(raw).decode(),
        }

    def _pba_pos80_product_name(self, product):
        name = " ".join((product.name or "").split())
        return name or product.display_name or "-"

    def _pba_pos80_product_code(self, product):
        return " ".join((product.default_code or "").split()) or "-"

    def _pba_pos80_location_label(self, location):
        if not location:
            return "-"
        return (
            location.complete_name
            or location.display_name
            or location.name
            or "-"
        )

    def _pba_pos80_move_line_qty(self, move_line):
        return move_line.quantity or getattr(move_line, "quantity_product_uom", 0) or 0

    def _pba_pos80_ticket_groups(self):
        self.ensure_one()
        moves = self.move_ids.filtered(
            lambda move: move.state != "cancel"
            and (move.product_uom_qty or move.quantity)
        )
        buckets = {}
        locations = {}
        products = {}

        def add_row(location, product, qty):
            if not qty:
                return
            loc_key = location.id if location else 0
            locations[loc_key] = location
            products[product.id] = product
            loc_bucket = buckets.setdefault(loc_key, {})
            loc_bucket[product.id] = loc_bucket.get(product.id, 0.0) + qty

        for move in moves:
            move_lines = move.move_line_ids.filtered(
                lambda line: line.state != "cancel"
            )
            grouped = {}
            for move_line in move_lines:
                location = move_line.location_id or move.location_id
                grouped[location] = grouped.get(
                    location, 0.0
                ) + self._pba_pos80_move_line_qty(move_line)
            if grouped and any(grouped.values()):
                for location, qty in grouped.items():
                    add_row(location, move.product_id, qty)
                continue
            add_row(
                move.location_id,
                move.product_id,
                move.quantity or move.product_uom_qty,
            )

        groups = []
        for loc_key in sorted(
            buckets,
            key=lambda key: self._pba_pos80_location_label(locations[key]).casefold(),
        ):
            items = []
            for product_id, qty in buckets[loc_key].items():
                product = products[product_id]
                items.append(
                    (
                        qty,
                        self._pba_pos80_product_code(product),
                        self._pba_pos80_product_name(product),
                    )
                )
            items.sort(key=lambda item: (item[1].casefold(), item[2].casefold()))
            groups.append((locations[loc_key], items))
        return groups

    def _pba_pos80_location_rows(self, location):
        label = self._pba_pos80_location_label(location)
        room = LINE_WIDTH - len(LOCATION_PREFIX)
        first, remain = _split_first_line(label, room)
        rows = [LOCATION_PREFIX + first]
        if remain:
            rows.extend(_wrap(remain))
        return rows

    def _pba_pos80_product_rows(self, qty, code, name):
        rows = [_clip("%s %s" % (_qty_cell(qty), code))]
        indent = " " * NAME_INDENT
        wrap_width = LINE_WIDTH - NAME_INDENT
        for chunk in _wrap(name, wrap_width):
            if chunk:
                rows.append(indent + chunk)
        return rows

    def _pba_pos80_ticket_bytes(self):
        self.ensure_one()
        partner = self.partner_id
        scheduled = self.scheduled_date or self.date_done or fields.Datetime.now()
        if isinstance(scheduled, datetime):
            scheduled = fields.Datetime.context_timestamp(
                self, fields.Datetime.to_datetime(scheduled)
            ).date()
        date_label = format_date(self.env, scheduled)
        parts = [
            b"\x1b\x40\x1b\x74\x10",
            b"\x1b\x61\x01",
            _encode(_center(_("Delivery")) + "\n"),
            b"\x1b\x45\x01",
            _encode(_center(self.name or "") + "\n"),
            b"\x1b\x45\x00",
            b"\x1b\x61\x00",
            _encode(("-" * LINE_WIDTH) + "\n"),
        ]
        if partner:
            customer_name = " ".join((partner.name or "").split())
            if customer_name:
                parts.append(_encode(_row(_("Customer"), customer_name) + "\n"))
            vat = (partner.vat or "").strip()
            if vat and vat != "/":
                parts.append(_encode(_row(_("VAT"), vat) + "\n"))
        if self.origin:
            parts.append(_encode(_row(_("Origin"), self.origin) + "\n"))
        parts.append(_encode(_row(_("Date"), date_label) + "\n"))
        parts.append(_encode(("-" * LINE_WIDTH) + "\n"))
        groups = self._pba_pos80_ticket_groups()
        if not groups:
            parts.append(_encode(_clip(_("No product lines")) + "\n"))
        for index, (location, items) in enumerate(groups):
            if index:
                parts.append(_encode("\n"))
            for row in self._pba_pos80_location_rows(location):
                parts.append(_encode(_clip(row) + "\n"))
            for qty, code, name in items:
                for row in self._pba_pos80_product_rows(qty, code, name):
                    parts.append(_encode(_clip(row) + "\n"))
        parts.append(_encode(("-" * LINE_WIDTH) + "\n"))
        scan = (self.name or "").strip()
        if scan and scan != "/":
            payload = ("{B" + scan).encode("ascii", "replace")
            parts.extend(
                [
                    b"\x1b\x61\x01",
                    b"\x1d\x48\x02",
                    b"\x1d\x68\x50",
                    b"\x1d\x77\x02",
                    b"\x1d\x6b\x49" + bytes([len(payload)]) + payload,
                    b"\n",
                    b"\x1b\x61\x00",
                ]
            )
        parts.extend([b"\n\n\n", b"\x1d\x56\x41\x03"])
        return b"".join(parts)
