# Copyright 2026 Alpha Agency Lifecycle Platform
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    is_auditor = fields.Boolean(
        string="Is Auditor",
        help="Can be assigned as auditor or corrective action owner.",
    )
    is_testing_directorate = fields.Boolean(
        string="Is Testing Directorate",
        help="Can be assigned as tester for device certification.",
    )
    is_licensing_officer = fields.Boolean(
        string="Is Licensing Officer",
        help="Can be assigned as issuing authority for licences.",
    )
