# Copyright 2026 Alpha Agency Lifecycle Platform
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError


class AgencyAudit(models.Model):
    """Audit lifecycle model (FR-12).

    Supports pre-onboarding audits, periodic audits, findings, corrective actions,
    and signed reports.
    """
    _name = "alpha.agency.audit"
    _description = "Agency Audit"
    _inherit = ["mail.thread", "mail.activity.mixin", "portal.mixin"]
    _order = "create_date desc"

    # ====================================================
    # Core Fields
    # ====================================================

    name = fields.Char(
        string="Audit Name",
        required=True,
        copy=False,
        tracking=True,
    )
    audit_code = fields.Char(
        string="Audit Code",
        readonly=True,
        copy=False,
        default=lambda self: "/",
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("planned", "Planned"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("findings", "Findings Identified"),
            ("corrective_action", "Corrective Action"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        string="State",
        default="planned",
        tracking=True,
    )
    priority = fields.Selection(
        selection=[
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
        string="Priority",
        default="medium",
        tracking=True,
    )

    # ====================================================
    # Agency Reference
    # ====================================================

    agency_id = fields.Many2one(
        comodel_name="alpha.agency",
        string="Agency",
        ondelete="restrict",
        index=True,
        required=True,
        tracking=True,
    )

    company_id = fields.Many2one(
    "res.company",
    string="Company",
    default=lambda self: self.env.company,
    required=True,
    index=True,
)

    # ====================================================
    # Audit Configuration
    # ====================================================

    audit_type = fields.Selection(
        selection=[
            ("pre_onboarding", "Pre-Onboarding"),
            ("periodic", "Periodic"),
            ("random", "Random"),
            ("special", "Special"),
        ],
        string="Audit Type",
        required=True,
        tracking=True,
    )
    cycle_type = fields.Selection(
        selection=[
            ("annual", "Annual"),
            ("quarterly", "Quarterly"),
            ("monthly", "Monthly"),
            ("ad_hoc", "Ad-hoc"),
        ],
        string="Cycle Type",
        default="annual",
        tracking=True,
    )
    scheduled_date = fields.Date(
        string="Scheduled Date",
        tracking=True,
    )
    actual_start_date = fields.Date(
        string="Actual Start Date",
        tracking=True,
    )
    actual_end_date = fields.Date(
        string="Actual End Date",
        tracking=True,
    )
    auditor_id = fields.Many2one(
        comodel_name="res.users",
        string="Auditor",
        domain="[('is_auditor', '=', True)]",
        tracking=True,
    )
    location = fields.Char(
        string="Location",
        tracking=True,
    )
    description = fields.Html(
        string="Audit Description",
        sanitize_style=True,
    )

    # ====================================================
    # Related Records
    # ====================================================

    evidence_ids = fields.One2many(
        comodel_name="dms.file",
        inverse_name="res_id",
        domain="[('res_model', '=', 'alpha.agency.audit')]",
        string="Evidence Documents",
    )
    finding_ids = fields.One2many(
        comodel_name="alpha.agency.audit.finding",
        inverse_name="audit_id",
        string="Audit Findings",
    )
    corrective_action_ids = fields.One2many(
        comodel_name="alpha.agency.audit.corrective.action",
        inverse_name="audit_id",
        string="Corrective Actions",
    )
    sign_request_id = fields.Many2one(
        comodel_name="sign.oca.request",
        string="Signed Report",
        readonly=True,
        tracking=True,
    )
    helpdesk_ticket_ids = fields.One2many(
        comodel_name="helpdesk.ticket",
        inverse_name="audit_id",
        string="Helpdesk Tickets",
    )

    # ====================================================
    # Computed Fields
    # ====================================================

    finding_count = fields.Integer(
        string="Total Findings",
        compute="_compute_finding_count",
        store=False,
    )
    open_finding_count = fields.Integer(
        string="Open Findings",
        compute="_compute_finding_count",
        store=False,
    )
    corrective_action_count = fields.Integer(
        string="Corrective Actions",
        compute="_compute_corrective_action_count",
        store=False,
    )
    open_corrective_action_count = fields.Integer(
        string="Open Corrective Actions",
        compute="_compute_corrective_action_count",
        store=False,
    )

    # ====================================================
    # Computation Methods
    # ====================================================

    @api.depends("finding_ids.state")
    def _compute_finding_count(self):
        for record in self:
            record.finding_count = len(record.finding_ids)
            record.open_finding_count = len(
                record.finding_ids.filtered(lambda f: f.state != "closed")
            )

    @api.depends("corrective_action_ids.state")
    def _compute_corrective_action_count(self):
        for record in self:
            record.corrective_action_count = len(record.corrective_action_ids)
            record.open_corrective_action_count = len(
                record.corrective_action_ids.filtered(lambda c: c.state != "done")
            )

    # ====================================================
    # Override Methods
    # ====================================================

    @api.model
    def create(self, vals):
        if vals.get("audit_code", "/") == "/":
            seq = self.env["ir.sequence"].next_by_code("alpha.agency.audit")
            vals["audit_code"] = seq
        return super().create(vals)

    # ====================================================
    # Actions
    # ====================================================

    def action_plan(self):
        """Plan the audit."""
        self.write({"state": "planned"})

    def action_start(self):
        """Start the audit."""
        self.ensure_one()
        self.write({
            "state": "in_progress",
            "actual_start_date": fields.Date.today(),
        })

    def action_complete(self):
        """Complete the audit - move to findings or close if no findings."""
        self.ensure_one()
        self.write({
            "state": "completed",
            "actual_end_date": fields.Date.today(),
        })

    def action_identify_findings(self):
        """Move to findings state for identified findings."""
        for record in self:
            if not record.finding_ids:
                raise ValidationError(
                    _("Cannot identify findings without any findings recorded.")
                )
            record.write({"state": "findings"})

    def action_corrective_action(self):
        """Move to corrective action state."""
        self.ensure_one()
        self.write({"state": "corrective_action"})

    def action_close(self):
        """Close the audit after corrective actions are done."""
        self.ensure_one()
        if self.corrective_action_ids.filtered(lambda c: c.state != "done"):
            raise ValidationError(
                _("Cannot close audit with pending corrective actions.")
            )
        self.write({"state": "closed"})

    def action_cancel(self):
        """Cancel the audit."""
        self.write({"state": "cancelled"})

    def action_generate_signed_report(self):
        """Generate and request signature for the audit report."""
        self.ensure_one()
        # Create PDF content (placeholder)
        pdf_content = b"Audit Report Content"

        self.env["sign.oca.request"].create({
            "name": _("Audit Report - %(name)s", name=self.name),
            "template_id": self.env.ref("sign_oca.sign_oca_template_audit_report").id,
            "data": pdf_content,
            "filename": f"audit_report_{self.audit_code}.pdf",
            "user_id": self.env.user.id,
            "record_ref": "alpha.agency.audit,%s" % self.id,
            "company_id": self.company_id.id,
        })

    # ====================================================
    # Portal Methods
    # ====================================================

    def _compute_access_url(self):
        for record in self:
            record.access_url = f"/my/agency/audit/{record.id}"


class AgencyAuditFinding(models.Model):
    """Audit findings model (FR-12)."""
    _name = "alpha.agency.audit.finding"
    _description = "Audit Finding"
    _order = "severity desc, create_date"

    name = fields.Char(
        string="Finding Title",
        required=True,
        tracking=True,
    )
    description = fields.Html(
        string="Description",
        sanitize_style=True,
        required=True,
    )
    severity = fields.Selection(
        selection=[
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
        string="Severity",
        default="medium",
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("open", "Open"),
            ("in_progress", "In Progress"),
            ("resolved", "Resolved"),
            ("closed", "Closed"),
            ("rejected", "Rejected"),
        ],
        string="State",
        default="open",
        tracking=True,
    )
    audit_id = fields.Many2one(
        comodel_name="alpha.agency.audit",
        string="Audit",
        ondelete="cascade",
        index=True,
        required=True,
    )
    agency_id = fields.Many2one(
        comodel_name="alpha.agency",
        string="Agency",
        related="audit_id.agency_id",
        store=True,
        readonly=True,
    )
    corrective_action_id = fields.Many2one(
        comodel_name="alpha.agency.audit.corrective.action",
        string="Corrective Action",
        ondelete="set null",
        readonly=True,
    )
    evidence_file_id = fields.Many2one(
        comodel_name="dms.file",
        string="Evidence",
        ondelete="set null",
    )
    resolution = fields.Text(
        string="Resolution Details",
    )
    resolved_date = fields.Date(
        string="Resolved Date",
        readonly=True,
    )
    created_by = fields.Many2one(
        comodel_name="res.users",
        string="Created By",
        readonly=True,
        default=lambda self: self.env.user,
    )

    def action_assign_corrective_action(self):
        """Assign a corrective action to this finding."""
        self.ensure_one()
        action = self.env["alpha.agency.audit.corrective.action"].create({
            "finding_id": self.id,
            "audit_id": self.audit_id.id,
            "agency_id": self.agency_id.id,
            "name": _("Corrective Action for %(finding)s", finding=self.name),
        })
        self.write({
            "corrective_action_id": action.id,
            "state": "in_progress",
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": "alpha.agency.audit.corrective.action",
            "view_mode": "form",
            "res_id": action.id,
            "target": "new",
        }

    def action_resolve(self):
        """Mark finding as resolved."""
        self.ensure_one()
        self.write({
            "state": "resolved",
            "resolved_date": fields.Date.today(),
        })

    def action_close(self):
        """Close the finding."""
        self.ensure_one()
        if self.state != "resolved":
            raise ValidationError(
                _("Only resolved findings can be closed.")
            )
        self.write({"state": "closed"})


class AgencyAuditCorrectiveAction(models.Model):
    """Corrective actions for audit findings."""
    _name = "alpha.agency.audit.corrective.action"
    _description = "Audit Corrective Action"
    _order = "create_date"

    name = fields.Char(
        string="Action Title",
        required=True,
        tracking=True,
    )
    description = fields.Text(
        string="Description",
        required=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        string="State",
        default="draft",
        tracking=True,
    )
    audit_id = fields.Many2one(
        comodel_name="alpha.agency.audit",
        string="Audit",
        ondelete="cascade",
        index=True,
        required=True,
    )
    finding_id = fields.Many2one(
        comodel_name="alpha.agency.audit.finding",
        string="Finding",
        ondelete="set null",
    )
    agency_id = fields.Many2one(
        comodel_name="alpha.agency",
        string="Agency",
        related="audit_id.agency_id",
        store=True,
        readonly=True,
    )
    assigned_to = fields.Many2one(
        comodel_name="res.users",
        string="Assigned To",
        domain="[('is_auditor', '=', True)]",
    )
    due_date = fields.Date(
        string="Due Date",
    )
    completed_date = fields.Date(
        string="Completed Date",
        readonly=True,
    )
    evidence_ids = fields.One2many(
        comodel_name="dms.file",
        inverse_name="res_id",
        domain="[('res_model', '=', 'alpha.agency.audit.corrective.action')]",
        string="Evidence Documents",
    )
    notes = fields.Text(
        string="Notes",
    )

    def action_start(self):
        """Start the corrective action."""
        self.write({"state": "in_progress"})

    def action_complete(self):
        """Mark corrective action as done."""
        self.write({
            "state": "done",
            "completed_date": fields.Date.today(),
        })
        # Close related finding
        if self.finding_id:
            self.finding_id.action_close()

    def action_cancel(self):
        """Cancel the corrective action."""
        self.write({"state": "cancelled"})