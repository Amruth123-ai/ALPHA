# Copyright 2026 Alpha Agency Lifecycle Platform
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _


class HelpdeskTicket(models.Model):
    """Extension of helpdesk.ticket to add agency-related fields."""
    _inherit = "helpdesk.ticket"

    # ====================================================
    # Agency Reference Fields
    # ====================================================

    alpha_agency_id = fields.Many2one(
        comodel_name="alpha.agency",
        string="Agency",
        ondelete="set null",
        index=True,
        tracking=True,
        help="Related agency for this ticket.",
    )
    application_id = fields.Many2one(
        comodel_name="alpha.agency.application",
        string="Agency Application",
        ondelete="set null",
        index=True,
        tracking=True,
        help="Related agency application.",
    )
    audit_id = fields.Many2one(
        comodel_name="alpha.agency.audit",
        string="Agency Audit",
        ondelete="set null",
        index=True,
        tracking=True,
        help="Related agency audit.",
    )
    licence_id = fields.Many2one(
        comodel_name="alpha.agency.licence",
        string="Agency Licence",
        ondelete="set null",
        index=True,
        tracking=True,
        help="Related agency licence.",
    )
    device_id = fields.Many2one(
        comodel_name="alpha.agency.device",
        string="Agency Device",
        ondelete="set null",
        index=True,
        tracking=True,
        help="Related agency device.",
    )

    # ====================================================
    # Related Records
    # ====================================================

    # Computed field to show related agency
    related_agency = fields.Char(
        string="Related Agency",
        compute="_compute_related_agency",
        store=False,
    )

    # ====================================================
    # Computation Methods
    # ====================================================

    @api.depends("alpha_agency_id", "application_id", "audit_id", "licence_id", "device_id")
    def _compute_related_agency(self):
        for record in self:
            if record.alpha_agency_id:
                record.related_agency = record.alpha_agency_id.name
            elif record.application_id and record.application_id.agency_id:
                record.related_agency = record.application_id.agency_id.name
            elif record.audit_id and record.audit_id.agency_id:
                record.related_agency = record.audit_id.agency_id.name
            elif record.licence_id and record.licence_id.agency_id:
                record.related_agency = record.licence_id.agency_id.name
            elif record.device_id and record.device_id.agency_id:
                record.related_agency = record.device_id.agency_id.name
            else:
                record.related_agency = False

    # ====================================================
    # Action Override
    # ====================================================

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        """Show always the stages without team, or stages of the default team."""
        search_domain = [
            "|",
            ("id", "in", stages.ids),
            ("team_ids", "=", False),
        ]
        default_team_id = self.default_get(["team_id"])
        if default_team_id:
            search_domain = [
                "|",
                ("team_ids", "=", default_team_id.get("team_id")),
            ] + search_domain
        return stages.search(search_domain)