from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

APPS_MENU_BACKGROUND_SIZE_PRESETS = [
    ("100", "100%"),
    ("70", "70%"),
    ("50", "50%"),
    ("40", "40%"),
    ("20", "20%"),
    ("custom", "Personalizado"),
]


class ResCompany(models.Model):
    _inherit = "res.company"

    apps_menu_background_image = fields.Image(
        string="Imagen de fondo del menú",
    )
    apps_menu_background_size = fields.Integer(
        string="Tamaño (%)",
        default=50,
        help="Porcentaje de la pantalla. Puede usar 100, 70, 50, 40, 20 u otro valor.",
    )
    apps_menu_background_size_preset = fields.Selection(
        selection=APPS_MENU_BACKGROUND_SIZE_PRESETS,
        string="Tamaño de pantalla",
        compute="_compute_apps_menu_background_size_preset",
        inverse="_inverse_apps_menu_background_size_preset",
        store=False,
    )
    apps_menu_background_position = fields.Selection(
        selection=[
            ("center", "Centrado"),
            ("top left", "Arriba izquierda"),
            ("top center", "Arriba centro"),
            ("top right", "Arriba derecha"),
            ("center left", "Centro izquierda"),
            ("center right", "Centro derecha"),
            ("bottom left", "Abajo izquierda"),
            ("bottom center", "Abajo centro"),
            ("bottom right", "Abajo derecha"),
        ],
        string="Posición",
        default="center",
    )
    apps_menu_background_opacity = fields.Integer(
        string="Opacidad (%)",
        default=100,
    )

    @api.depends("apps_menu_background_size")
    def _compute_apps_menu_background_size_preset(self):
        presets = {"100", "70", "50", "40", "20"}
        for company in self:
            size = str(company.apps_menu_background_size or 50)
            company.apps_menu_background_size_preset = (
                size if size in presets else "custom"
            )

    def _inverse_apps_menu_background_size_preset(self):
        for company in self:
            if company.apps_menu_background_size_preset != "custom":
                company.apps_menu_background_size = int(
                    company.apps_menu_background_size_preset
                )

    @api.onchange("apps_menu_background_size_preset")
    def _onchange_apps_menu_background_size_preset(self):
        if (
            self.apps_menu_background_size_preset
            and self.apps_menu_background_size_preset != "custom"
        ):
            self.apps_menu_background_size = int(self.apps_menu_background_size_preset)

    @api.constrains("apps_menu_background_size")
    def _check_apps_menu_background_size(self):
        for company in self:
            if not 1 <= company.apps_menu_background_size <= 100:
                raise ValidationError(
                    _("El tamaño de la imagen de fondo debe estar entre 1 y 100.")
                )

    @api.constrains("apps_menu_background_opacity")
    def _check_apps_menu_background_opacity(self):
        for company in self:
            if not 0 <= company.apps_menu_background_opacity <= 100:
                raise ValidationError(
                    _("La opacidad de la imagen de fondo debe estar entre 0 y 100.")
                )

    def _get_apps_menu_background_info(self):
        self.ensure_one()
        attachment = (
            self.env["ir.attachment"]
            .sudo()
            .search(
                [
                    ("res_model", "=", "res.company"),
                    ("res_id", "=", self.id),
                    ("res_field", "=", "apps_menu_background_image"),
                ],
                limit=1,
            )
        )
        if not attachment:
            return {}
        unique = fields.Datetime.to_string(attachment.write_date or self.write_date)
        return {
            "url": "/web/image/res.company/%s/apps_menu_background_image?unique=%s"
            % (self.id, unique),
            "size": self.apps_menu_background_size or 50,
            "position": self.apps_menu_background_position or "center",
            "opacity": (self.apps_menu_background_opacity or 0) / 100.0,
        }
