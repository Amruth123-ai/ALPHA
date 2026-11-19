from odoo import fields, models


class ResGroups(models.Model):
    _inherit = "res.groups"

    category_id = fields.Many2one(
        "ir.module.category",
        string="Category",
    )