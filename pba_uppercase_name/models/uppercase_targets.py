from odoo import api, models

from .pba_uppercase_name_helpers import (
    pba_uppercase_name_in_vals,
    pba_uppercase_name_in_vals_list,
)


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model_create_multi
    def create(self, vals_list):
        pba_uppercase_name_in_vals_list(self, vals_list)
        return super().create(vals_list)

    def write(self, vals):
        pba_uppercase_name_in_vals(self, vals)
        return super().write(vals)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model_create_multi
    def create(self, vals_list):
        pba_uppercase_name_in_vals_list(self, vals_list)
        return super().create(vals_list)

    def write(self, vals):
        pba_uppercase_name_in_vals(self, vals)
        return super().write(vals)


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model_create_multi
    def create(self, vals_list):
        pba_uppercase_name_in_vals_list(self, vals_list)
        return super().create(vals_list)

    def write(self, vals):
        pba_uppercase_name_in_vals(self, vals)
        return super().write(vals)


class ProductBrand(models.Model):
    _inherit = "product.brand"

    @api.model_create_multi
    def create(self, vals_list):
        pba_uppercase_name_in_vals_list(self, vals_list)
        return super().create(vals_list)

    def write(self, vals):
        pba_uppercase_name_in_vals(self, vals)
        return super().write(vals)


class ProductCategory(models.Model):
    _inherit = "product.category"

    @api.model_create_multi
    def create(self, vals_list):
        pba_uppercase_name_in_vals_list(self, vals_list)
        return super().create(vals_list)

    def write(self, vals):
        pba_uppercase_name_in_vals(self, vals)
        return super().write(vals)


class AccountAccount(models.Model):
    _inherit = "account.account"

    @api.model_create_multi
    def create(self, vals_list):
        pba_uppercase_name_in_vals_list(self, vals_list)
        return super().create(vals_list)

    def write(self, vals):
        pba_uppercase_name_in_vals(self, vals)
        return super().write(vals)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.model_create_multi
    def create(self, vals_list):
        pba_uppercase_name_in_vals_list(self, vals_list)
        return super().create(vals_list)

    def write(self, vals):
        pba_uppercase_name_in_vals(self, vals)
        return super().write(vals)
