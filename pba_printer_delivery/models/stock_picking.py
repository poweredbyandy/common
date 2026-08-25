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


def _qty_label(qty):
    if qty == int(qty):
        return str(int(qty))
    return ("%.2f" % qty).rstrip("0").rstrip(".")


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.model_create_multi
    def create(self, vals_list):
        pickings = super().create(vals_list)
        pickings._pba_pos80_autoprint()
        return pickings

    def action_print_pos80(self):
        return {
            "type": "ir.actions.client",
            "tag": "pba_printer_delivery_print",
            "params": {
                "picking_ids": self.ids,
            },
        }

    @api.model
    def get_pos80_print_payload(self, picking_ids):
        self._pba_pos80_ensure_device()
        pickings = self.browse(picking_ids).exists()
        return [picking._pba_pos80_ticket_payload() for picking in pickings]

    def _pba_pos80_autoprint(self):
        if self.env.context.get("install_mode"):
            return
        for picking in self:
            if not picking._pba_pos80_should_autoprint():
                continue
            try:
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
        if self.picking_type_code != "outgoing":
            return False
        return bool(self.company_id.pba_pos80_auto_print)

    def _pba_pos80_ensure_device(self):
        if "device.bridge" not in self.env:
            return
        from odoo.addons.pba_printer_delivery.hooks import post_init_hook

        post_init_hook(self.env)

    def _pba_pos80_try_gateway_print(self, payload):
        if "device.bridge.gateway" not in self.env:
            return False
        self._pba_pos80_ensure_device()
        try:
            self.env["device.bridge.gateway"].send_raw_job(
                payload["device_code"],
                payload["data_b64"],
            )
            return True
        except Exception:
            _logger.debug("POS-80 gateway print skipped", exc_info=True)
            return False

    def _pba_pos80_notify_local_print(self, payload):
        group = self.env.ref(
            "pba_bus_picking_notification.group_stock_picking_bus_notify",
            raise_if_not_found=False,
        )
        if group:
            group._bus_send(POS80_PRINT_NOTIFICATION, payload)
            return
        self.env.user._bus_send(POS80_PRINT_NOTIFICATION, payload)

    def _pba_pos80_ticket_payload(self):
        self.ensure_one()
        raw = self._pba_pos80_ticket_bytes()
        return {
            "picking_id": self.id,
            "name": self.name,
            "device_code": POS80_DEVICE_CODE,
            "data_b64": base64.b64encode(raw).decode(),
        }

    def _pba_pos80_ticket_lines(self):
        self.ensure_one()
        moves = self.move_ids.filtered(
            lambda move: move.state != "cancel"
            and (move.product_uom_qty or move.quantity)
        )
        rows = []
        for move in moves:
            qty = move.quantity or move.product_uom_qty
            name = " ".join((move.product_id.display_name or "").split())
            code = (move.product_id.default_code or "").strip()
            if code and name.startswith("[%s]" % code):
                name = name[len(code) + 2 :].strip()
            rows.append((_qty_label(qty), name or move.product_id.name or "-"))
        return rows

    def _pba_pos80_ticket_bytes(self):
        self.ensure_one()
        company = self.company_id or self.env.company
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
            b"\x1d\x21\x11",
            _encode(_center(company.name or "", 24) + "\n"),
            b"\x1d\x21\x00",
            _encode(_center(_("Delivery")) + "\n"),
            b"\x1b\x45\x01",
            _encode(_center(self.name or "") + "\n"),
            b"\x1b\x45\x00",
            b"\x1b\x61\x00",
            _encode(("-" * LINE_WIDTH) + "\n"),
        ]
        if partner:
            parts.append(_encode(_row(_("Customer"), partner.display_name) + "\n"))
            if partner.vat:
                parts.append(_encode(_row(_("VAT"), partner.vat) + "\n"))
        if self.origin:
            parts.append(_encode(_row(_("Origin"), self.origin) + "\n"))
        parts.append(_encode(_row(_("Date"), date_label) + "\n"))
        parts.append(_encode(("-" * LINE_WIDTH) + "\n"))
        lines = self._pba_pos80_ticket_lines()
        if not lines:
            parts.append(_encode(_clip(_("No product lines")) + "\n"))
        for qty, name in lines:
            qty_cell = qty.rjust(5)
            desc_width = LINE_WIDTH - 6
            first = True
            remain = name
            while remain or first:
                chunk = remain[:desc_width]
                remain = remain[desc_width:]
                prefix = qty_cell if first else " " * 5
                parts.append(_encode("%s %s\n" % (prefix, chunk)))
                first = False
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
