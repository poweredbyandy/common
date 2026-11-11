from odoo import models


class ExtendExistingModel(models.Model):
    """Keep fields from another addon that already registered the same _name."""

    _register = False

    @classmethod
    def _build_model(cls, pool, cr):
        original = cls._inherit
        names = (
            list(original)
            if isinstance(original, (list, tuple))
            else ([original] if original else [])
        )
        try:
            if cls._name in pool and cls._name not in names:
                cls._inherit = names + [cls._name]
            return super()._build_model(pool, cr)
        finally:
            cls._inherit = original
