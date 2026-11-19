# Copyright 2026 Alpha Agency Lifecycle Platform
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError


class AgencyWorkflow(models.Model):
    """Workflow designer and version control (FR-05, FR-07).

    Manages configurable workflows for agency onboarding, compliance,
    audits, and certifications with version control.
    """
    _name = "alpha.agency.workflow"
    _description = "Agency Workflow"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    # ====================================================
    # Core Fields
    # ====================================================

    name = fields.Char(
        string="Workflow Name",
        required=True,
        tracking=True,
    )
    code = fields.Char(
        string="Code",
        required=True,
        tracking=True,
    )
    description = fields.Text(
        string="Description",
    )
    is_active = fields.Boolean(
        string="Active",
        default=True,
        tracking=True,
    )
    is_configurable = fields.Boolean(
        string="Configurable",
        default=True,
        help="Allow workflow steps to be configured by users.",
        tracking=True,
    )

    # ====================================================
    # Agency Type Configuration
    # ====================================================

    agency_type = fields.Selection(
        selection=[
            ("type_a", "Type A - User Agency"),
            ("type_b", "Type B - KYC User Agency"),
            ("type_c", "Type C - Service Provider Agency"),
            ("type_d", "Type D - Sub-user Agency"),
            ("type_e", "Type E - Sub-KYC User Agency"),
            ("all", "All Agency Types"),
        ],
        string="Agency Type",
        required=True,
        tracking=True,
    )
    applicable_agency_id = fields.Many2many(
        comodel_name="alpha.agency",
        relation="alpha_workflow_agency_rel",
        column1="workflow_id",
        column2="agency_id",
        string="Applicable Agencies",
    )

    company_id = fields.Many2one(
    "res.company",
    string="Company",
    default=lambda self: self.env.company,
    required=True,
    index=True,
)

    # ====================================================
    # Workflow Process Fields
    # ====================================================

    document_type = fields.Selection(
        selection=[
            ("application", "Agency Application"),
            ("audit", "Agency Audit"),
            ("licence", "Agency Licence"),
            ("device", "Agency Device"),
            ("all_docs", "All Document Types"),
        ],
        string="Document Type",
        required=True,
        tracking=True,
    )
    current_version = fields.Char(
        string="Current Version",
        default="1.0.0",
        tracking=True,
    )
    is_versioned = fields.Boolean(
        string="Versioned",
        default=True,
        help="Track workflow changes with version numbers.",
        tracking=True,
    )

    # ====================================================
    # Status Fields
    # ====================================================

    status = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("review", "Under Review"),
            ("published", "Published"),
            ("archived", "Archived"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )

    # ====================================================
    # Related Records
    # ====================================================

    version_ids = fields.One2many(
        comodel_name="alpha.agency.workflow.version",
        inverse_name="workflow_id",
        string="Workflow Versions",
    )
    active_version_id = fields.Many2one(
        comodel_name="alpha.agency.workflow.version",
        string="Active Version",
        ondelete="set null",
        tracking=True,
    )
    step_ids = fields.One2many(
        comodel_name="alpha.agency.workflow.step",
        inverse_name="workflow_id",
        string="Workflow Steps",
    )
    approval_rule_id = fields.Many2one(
        comodel_name="alpha.agency.workflow.approval",
        string="Approval Rule",
        ondelete="set null",
        tracking=True,
    )

    # ====================================================
    # Computed Fields
    # ====================================================

    step_count = fields.Integer(
        string="Total Steps",
        compute="_compute_step_count",
        store=False,
    )
    active_step_count = fields.Integer(
        string="Active Steps",
        compute="_compute_step_count",
        store=False,
    )
    last_modified_date = fields.Datetime(
        string="Last Modified",
        default=fields.Datetime.now,
        tracking=True,
    )

    # ====================================================
    # Computation Methods
    # ====================================================

    @api.depends("step_ids")
    def _compute_step_count(self):
        for record in self:
            record.step_count = len(record.step_ids)
            record.active_step_count = len(
                record.step_ids.filtered(lambda s: s.is_active)
            )

    # ====================================================
    # Constraints
    # ====================================================

    @api.constrains("code")
    def _check_code_unique(self):
        for record in self:
            existing = self.search([
                ("code", "=", record.code),
                ("id", "!=", record.id),
                ("status", "in", ["published", "review"]),
            ])
            if existing:
                raise ValidationError(
                    _("Workflow code must be unique for active/published workflows."))

    # ====================================================
    # Override Methods
    # ====================================================

    @api.model
    def create(self, vals):
        if vals.get("current_version") == "1.0.0" and not vals.get("status") == "draft":
            vals["status"] = "draft"
        return super().create(vals)

    # ====================================================
    # Actions
    # ====================================================

    def action_draft(self):
        """Set workflow to draft."""
        self.write({"status": "draft"})

    def action_review(self):
        """Send workflow to review."""
        if not self.step_ids:
            raise ValidationError(
                _("Workflow must have at least one step."))
        self.write({"status": "review"})

    def action_publish(self):
        """Publish the workflow."""
        if self.status != "review":
            raise ValidationError(
                _("Workflow must be in Review status to publish."))

        # Create new version
        version = self.env["alpha.agency.workflow.version"].create({
            "workflow_id": self.id,
            "version_number": self.current_version,
            "name": f"{self.name} v{self.current_version}",
        })

        # Set as active version
        self.write({
            "status": "published",
            "active_version_id": version.id,
            "last_modified_date": fields.Datetime.now(),
        })

    def action_archive(self):
        """Archive the workflow."""
        self.write({
            "status": "archived",
            "is_active": False,
        })

    def action_create_version(self):
        """Create a new version for the workflow."""
        self.ensure_one()
        if self.status == "draft":
            # Update current version number
            version_parts = self.current_version.split(".")
            if len(version_parts) == 3:
                major, minor, patch = version_parts
                new_patch = str(int(patch) + 1)
                self.current_version = f"{major}.{minor}.{new_patch}"
            else:
                self.current_version = "1.0.1"

            # Create version record
            self.env["alpha.agency.workflow.version"].create({
                "workflow_id": self.id,
                "version_number": self.current_version,
                "name": f"{self.name} v{self.current_version}",
            })

    # ====================================================
    # Helper Methods
    # ====================================================

    def get_next_step(self, current_step_code):
        """Get the next step in the workflow based on current step."""
        next_step = self.step_ids.search([
            ("workflow_id", "=", self.id),
            ("previous_step_code", "=", current_step_code),
            ("is_active", "=", True),
        ], order="sequence")
        return next_step

    def get_steps_by_type(self, step_type):
        """Get steps filtered by type."""
        return self.step_ids.filtered(lambda s: s.step_type == step_type)

    # ====================================================
    # Portal Methods
    # ====================================================

    def _compute_access_url(self):
        for record in self:
            record.access_url = f"/my/agency/workflow/{record.id}"


class AgencyWorkflowVersion(models.Model):
    """Workflow version tracking (FR-07)."""
    _name = "alpha.agency.workflow.version"
    _description = "Agency Workflow Version"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(
        string="Version Name",
        required=True,
        tracking=True,
    )
    version_number = fields.Char(
        string="Version Number",
        required=True,
        tracking=True,
    )
    workflow_id = fields.Many2one(
        comodel_name="alpha.agency.workflow",
        string="Workflow",
        ondelete="cascade",
        index=True,
        required=True,
    )
    created_by = fields.Many2one(
        comodel_name="res.users",
        string="Created By",
        readonly=True,
        default=lambda self: self.env.user,
        tracking=True,
    )
    create_date = fields.Datetime(
        string="Created On",
        readonly=True,
        default=fields.Datetime.now,
        tracking=True,
    )
    is_active = fields.Boolean(
        string="Active",
        default=False,
        tracking=True,
    )
    change_reason = fields.Text(
        string="Change Reason",
        help="Reason for creating this version.",
    )
    is_approved = fields.Boolean(
        string="Approved",
        default=False,
        tracking=True,
    )
    approved_by = fields.Many2one(
        comodel_name="res.users",
        string="Approved By",
        tracking=True,
    )
    approval_date = fields.Datetime(
        string="Approval Date",
        tracking=True,
    )

    company_id = fields.Many2one(
        "res.company",
        related="workflow_id.company_id",
        store=True,
        index=True,
        readonly=True,
    )

    @api.constrains("workflow_id", "is_active")
    def _check_single_active_version(self):
        for record in self:
            if record.is_active:
                existing = self.search([
                    ("workflow_id", "=", record.workflow_id.id),
                    ("is_active", "=", True),
                    ("id", "!=", record.id),
                ])
                if existing:
                    raise ValidationError(
                        _("Only one version can be active per workflow."))


class AgencyWorkflowStep(models.Model):
    """Workflow step definition."""
    _name = "alpha.agency.workflow.step"
    _description = "Agency Workflow Step"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence"

    name = fields.Char(
        string="Step Name",
        required=True,
        tracking=True,
    )
    code = fields.Char(
        string="Step Code",
        required=True,
        tracking=True,
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
        tracking=True,
    )
    workflow_id = fields.Many2one(
        comodel_name="alpha.agency.workflow",
        string="Workflow",
        ondelete="cascade",
        index=True,
        required=True,
    )
    step_type = fields.Selection(
        selection=[
            ("document_upload", "Document Upload"),
            ("review", "Review"),
            ("approval", "Approval"),
            ("ai_scrutiny", "AI Scrutiny"),
            ("manual_review", "Manual Review"),
            ("signing", "Digital Signing"),
            ("notification", "Notification"),
            ("custom", "Custom Action"),
        ],
        string="Step Type",
        required=True,
        tracking=True,
    )
    is_active = fields.Boolean(
        string="Active",
        default=True,
        tracking=True,
    )
    is_required = fields.Boolean(
        string="Required",
        default=True,
        tracking=True,
    )
    is_parallel = fields.Boolean(
        string="Parallel Execution",
        default=False,
        help="Execute this step in parallel with other steps.",
    )
    previous_step_code = fields.Char(
        string="Previous Step Code",
        help="Code of the step that must be completed before this step.",
    )
    next_step_codes = fields.Char(
        string="Next Step Codes",
        help="Comma-separated list of next step codes.",
    )
    assignee_field = fields.Char(
        string="Assignee Field",
        help="Field name to determine assignee (e.g., 'auditor_id', 'approver_id').",
    )
    duration_days = fields.Integer(
        string="Expected Duration (Days)",
        help="Expected time to complete this step.",
    )
    notification_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Notification Template",
        ondelete="set null",
    )
    company_id = fields.Many2one(
        "res.company",
        related="workflow_id.company_id",
        store=True,
        index=True,
        readonly=True,
    )

    # ====================================================
    # Constraints
    # ====================================================

    @api.constrains("code", "workflow_id")
    def _check_unique_step_code(self):
        for record in self:
            existing = self.search([
                ("code", "=", record.code),
                ("workflow_id", "=", record.workflow_id.id),
                ("id", "!=", record.id),
            ])
            if existing:
                raise ValidationError(
                    _("Step code must be unique within a workflow."))

    # ====================================================
    # Helper Methods
    # ====================================================

    def get_next_steps(self):
        """Get the next steps after this step."""
        next_codes = [c.strip() for c in self.next_step_codes.split(",") if c.strip()]
        if next_codes:
            return self.search([
                ("workflow_id", "=", self.workflow_id.id),
                ("code", "in", next_codes),
                ("is_active", "=", True),
            ])
        return self.env["alpha.agency.workflow.step"]


class AgencyWorkflowApproval(models.Model):
    """Approval rule for workflows."""
    _name = "alpha.agency.workflow.approval"
    _description = "Agency Workflow Approval Rule"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence"

    name = fields.Char(
        string="Approval Rule Name",
        required=True,
        tracking=True,
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
        tracking=True,
    )
    workflow_id = fields.Many2one(
        comodel_name="alpha.agency.workflow",
        string="Workflow",
        ondelete="cascade",
        index=True,
    )
    approval_type = fields.Selection(
        selection=[
            ("single", "Single Approver"),
            ("multiple", "Multiple Approvers"),
            ("any", "Any Approver"),
            ("all", "All Approvers"),
        ],
        string="Approval Type",
        default="single",
        required=True,
        tracking=True,
    )
    required_approver_count = fields.Integer(
        string="Required Approvers",
        default=1,
        help="Number of approvers required (for single/any type).",
    )
    approver_user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="alpha_workflow_approver_user_rel",
        column1="approval_id",
        column2="user_id",
        string="Approvers",
    )
    approver_group_id = fields.Many2one(
        comodel_name="res.groups",
        string="Approver Group",
        ondelete="set null",
        help="Approvers must belong to this group.",
    )
    duration_days = fields.Integer(
        string="Approval Duration (Days)",
        default=7,
        help="Days allowed for approval.",
    )
    company_id = fields.Many2one(
        "res.company",
        related="workflow_id.company_id",
        store=True,
        index=True,
        readonly=True,
    )


class AgencyWorkflowTransition(models.Model):
    """State transition definition for workflow."""
    _name = "alpha.agency.workflow.transition"
    _description = "Agency Workflow Transition"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence"

    name = fields.Char(
        string="Transition Name",
        required=True,
        tracking=True,
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
        tracking=True,
    )
    source_state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("under_review", "Under Review"),
            ("ai_scrutiny", "AI Scrutiny"),
            ("compliance_gaps", "Compliance Gaps"),
            ("agency_fixes", "Agency Fixing"),
            ("pending_approval", "Pending Approval"),
            ("rejected", "Rejected"),
            ("returned", "Returned"),
            ("approved", "Approved"),
            ("cancelled", "Cancelled"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("findings", "Findings"),
            ("corrective_action", "Corrective Action"),
            ("closed", "Closed"),
            ("active", "Active"),
            ("suspended", "Suspended"),
            ("expired", "Expired"),
        ],
        string="Source State",
        required=True,
    )
    target_state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("under_review", "Under Review"),
            ("ai_scrutiny", "AI Scrutiny"),
            ("compliance_gaps", "Compliance Gaps"),
            ("agency_fixes", "Agency Fixing"),
            ("pending_approval", "Pending Approval"),
            ("rejected", "Rejected"),
            ("returned", "Returned"),
            ("approved", "Approved"),
            ("cancelled", "Cancelled"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("findings", "Findings"),
            ("corrective_action", "Corrective Action"),
            ("closed", "Closed"),
            ("active", "Active"),
            ("suspended", "Suspended"),
            ("expired", "Expired"),
        ],
        string="Target State",
        required=True,
    )
    is_allowed = fields.Boolean(
        string="Allowed",
        default=True,
    )
    condition_domain = fields.Text(
        string="Condition Domain",
        help="Domain condition for transition (Python expression).",
    )
    is_auto_transition = fields.Boolean(
        string="Auto Transition",
        default=False,
        help="Automatically transition when condition is met.",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )

    @api.constrains("source_state", "target_state")
    def _check_valid_transition(self):
        for record in self:
            if record.source_state == record.target_state:
                raise ValidationError(
                    _("Source and target states cannot be the same."))

    def check_conditions(self, record):
        """Check if transition conditions are met."""
        if not self.condition_domain:
            return True
        try:
            domain = eval(self.condition_domain, {
                'record': record,
                'self': self,
            })
            return bool(domain)
        except Exception:
            return False