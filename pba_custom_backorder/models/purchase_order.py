from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    pba_is_supplier_backorder = fields.Boolean(
        string="Backorder de proveedor",
        default=False,
        copy=False,
    )
    pba_backorder_confirmation = fields.Char(
        string="Confirmación backorder",
        copy=False,
        index=True,
    )
    pba_backorder_factory = fields.Char(
        string="Fábrica / marca",
        copy=False,
    )
    pba_backorder_import_filename = fields.Char(
        string="Archivo importado",
        copy=False,
    )
    pba_backorder_file_hash = fields.Char(
        string="Hash archivo importado",
        copy=False,
        index=True,
    )

    @api.model
    def _pba_normalize_confirmation(self, confirmation_ref):
        if not confirmation_ref:
            return False
        normalized = str(confirmation_ref).strip()
        return normalized or False

    @api.model
    def _pba_backorder_base_domain(self, company_id=None):
        cid = (
            company_id.id
            if hasattr(company_id, "id")
            else (company_id or self.env.company.id)
        )
        return [
            ("company_id", "=", cid),
            ("state", "!=", "cancel"),
        ]

    @api.model
    def _pba_find_by_file_hash(self, file_hash, company_id=None):
        if not file_hash:
            return self.browse()
        domain = self._pba_backorder_base_domain(company_id) + [
            ("pba_backorder_file_hash", "=", file_hash),
        ]
        return self.search(domain, order="id desc", limit=1)

    @api.model
    def _pba_find_by_confirmation(self, confirmation_ref, company_id=None):
        confirmation_ref = self._pba_normalize_confirmation(confirmation_ref)
        if not confirmation_ref:
            return self.browse()
        domain = self._pba_backorder_base_domain(company_id) + [
            ("pba_backorder_confirmation", "=", confirmation_ref),
        ]
        return self.search(domain, order="id desc", limit=1)

    @api.model
    def _pba_find_supplier_backorder(
        self, confirmation_ref, company_id=None, file_hash=None
    ):
        if file_hash:
            po = self._pba_find_by_file_hash(file_hash, company_id=company_id)
            if po:
                return po
        if confirmation_ref:
            return self._pba_find_by_confirmation(
                confirmation_ref, company_id=company_id
            )
        return self.browse()

    @api.constrains(
        "pba_is_supplier_backorder",
        "pba_backorder_file_hash",
        "company_id",
        "state",
    )
    def _check_pba_backorder_file_hash_unique(self):
        for order in self.filtered(
            lambda o: o.pba_is_supplier_backorder and o.pba_backorder_file_hash
        ):
            duplicate = self.search_count(
                [
                    ("id", "!=", order.id),
                    ("pba_is_supplier_backorder", "=", True),
                    ("pba_backorder_file_hash", "=", order.pba_backorder_file_hash),
                    ("company_id", "=", order.company_id.id),
                    ("state", "!=", "cancel"),
                ]
            )
            if duplicate:
                raise ValidationError(
                    _(
                        "Este archivo Excel ya fue importado en la orden %(name)s.",
                        name=self.search(
                            [
                                ("pba_backorder_file_hash", "=", order.pba_backorder_file_hash),
                                ("company_id", "=", order.company_id.id),
                                ("state", "!=", "cancel"),
                                ("id", "!=", order.id),
                            ],
                            limit=1,
                        ).name,
                    )
                )

    @api.constrains(
        "pba_is_supplier_backorder",
        "pba_backorder_confirmation",
        "pba_backorder_file_hash",
        "company_id",
        "state",
    )
    def _check_pba_backorder_confirmation_unique(self):
        for order in self.filtered(
            lambda o: o.pba_is_supplier_backorder
            and o._pba_normalize_confirmation(o.pba_backorder_confirmation)
        ):
            confirmation = order._pba_normalize_confirmation(
                order.pba_backorder_confirmation
            )
            domain = [
                ("id", "!=", order.id),
                ("pba_is_supplier_backorder", "=", True),
                ("pba_backorder_confirmation", "=", confirmation),
                ("company_id", "=", order.company_id.id),
                ("state", "!=", "cancel"),
            ]
            if order.pba_backorder_file_hash:
                domain.append(
                    ("pba_backorder_file_hash", "=", order.pba_backorder_file_hash)
                )
            duplicate = self.search_count(domain)
            if duplicate:
                raise ValidationError(
                    _(
                        "La confirmación de backorder %(ref)s ya está registrada "
                        "para este mismo archivo en otra orden de compra.",
                        ref=confirmation,
                    )
                )
