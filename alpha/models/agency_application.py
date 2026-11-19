# Copyright 2026 Alpha Agency Lifecycle Platform
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError


class AgencyApplication(models.Model):
    """Agency Application model managing applications, validations, and approvals.

    Implements the pre-onboarding scrutiny (FR-01) and agency portal (FR-02) requirements.
    """
    _name = "alpha.agency.application"
    _description = "Agency Application"
    _inherit = ["mail.thread", "mail.activity.mixin", "portal.mixin"]
    _order = "create_date desc"

    # ====================================================
    # Core Fields
    # ====================================================

    name = fields.Char(
        string="Application Title",
        required=True,
        copy=False,
        tracking=True,
    )
    application_number = fields.Char(
        string="Application Number",
        readonly=True,
        copy=False,
        default=lambda self: "/",
        tracking=True,
    )
    state = fields.Selection(
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
        ],
        string="Status",
        default="draft",
        tracking=True,
    )
    priority = fields.Selection(
        selection=[
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("urgent", "Urgent"),
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
        ondelete="cascade",
        index=True,
        required=True,
        tracking=True,
    )
    agency_type = fields.Selection(
        selection=[
            ("type_a", "Type A - User Agency"),
            ("type_b", "Type B - KYC User Agency"),
            ("type_c", "Type C - Service Provider Agency"),
            ("type_d", "Type D - Sub-user Agency"),
            ("type_e", "Type E - Sub-KYC User Agency"),
        ],
        string="Agency Type",
        related="agency_id.agency_type",
        store=True,
        readonly=True,
    )

    # ====================================================
    # Application Fields
    # ====================================================

    application_date = fields.Datetime(
        string="Application Date",
        default=fields.Datetime.now,
        tracking=True,
    )
    submission_date = fields.Datetime(
        string="Submission Date",
        tracking=True,
    )
    approval_date = fields.Datetime(
        string="Approval Date",
        tracking=True,
    )
    rejection_reason = fields.Text(
        string="Rejection Reason",
    )
    return_reason = fields.Text(
        string="Return Reason",
    )

    # ====================================================
    # User and Communication
    # ====================================================

    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Created By",
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Applicant",
        ondelete="restrict",
        tracking=True,
    )
    email = fields.Char(
        string="Email",
        tracking=True,
    )
    phone = fields.Char(
        string="Phone",
        tracking=True,
    )

    # ====================================================
    # Document and Compliance
    # ====================================================

    document_ids = fields.One2many(
        comodel_name="alpha.agency.application.document",
        inverse_name="application_id",
        string="Application Documents",
    )
    compliance_requirement_ids = fields.Many2many(
        comodel_name="alpha.compliance.requirement",
        relation="alpha_agency_application_compliance_rel",
        column1="application_id",
        column2="compliance_requirement_id",
        string="Compliance Requirements",
    )
    ai_scrutiny_summary = fields.Text(
        string="AI Scrutiny Summary",
        readonly=True,
        tracking=True,
    )
    ai_results_json = fields.Json(
        string="AI Results",
        readonly=True,
        tracking=True,
    )
    officer_override = fields.Boolean(
        string="Officer Override Applied",
        readonly=True,
        tracking=True,
    )
    override_reason = fields.Text(
        string="Override Reason",
        readonly=True,
    )

    # ====================================================
    # Company Field (from Agency)
    # ====================================================

    company_id = fields.Many2one(
        "res.company",
        related="agency_id.company_id",
        store=True,
        index=True,
        readonly=True,
    )

    # ====================================================
    # Approval Fields
    # ====================================================

    approver_id = fields.Many2one(
        comodel_name="res.users",
        string="Approver",
        readonly=True,
        tracking=True,
    )
    approver_comments = fields.Text(
        string="Approver Comments",
    )

    # ====================================================
    # Related Records
    # ====================================================

    helpdesk_ticket_ids = fields.One2many(
        comodel_name="helpdesk.ticket",
        inverse_name="application_id",
        string="Helpdesk Tickets",
    )
    sign_request_id = fields.Many2one(
        comodel_name="sign.oca.request",
        string="Signature Request",
        readonly=True,
        tracking=True,
    )

    # ====================================================
    # Computed Fields
    # ====================================================

    document_count = fields.Integer(
        string="Documents",
        compute="_compute_document_count",
        store=False,
    )
    is_compliant = fields.Boolean(
        string="Compliant",
        compute="_compute_compliance_status",
        store=True,
    )
    missing_requirements_count = fields.Integer(
        string="Missing Requirements",
        compute="_compute_compliance_status",
        store=False,
    )

    # ====================================================
    # Computation Methods
    # ====================================================

    @api.depends("document_ids")
    def _compute_document_count(self):
        for record in self:
            record.document_count = len(record.document_ids)

    @api.depends("compliance_requirement_ids", "document_ids.mapping_id")
    def _compute_compliance_status(self):
        for record in self:
            # Check if all requirements are mapped to documents
            req_count = len(record.compliance_requirement_ids)
            mapped_count = len(
                record.document_ids.filtered(lambda d: d.mapping_id)
            )
            record.is_compliant = req_count > 0 and req_count == mapped_count
            record.missing_requirements_count = req_count - mapped_count

    # ====================================================
    # Constraints
    # ====================================================

    @api.constrains("state")
    def _check_state_transitions(self):
        for record in self:
            if record.state == "approved" and not record.is_compliant:
                raise ValidationError(
                    _("Cannot approve application with missing compliance requirements.")
                )

    # ====================================================
    # Override Methods
    # ====================================================

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("application_number", "/") == "/":
                seq = self.env["ir.sequence"].next_by_code("alpha.agency.application")
                vals["application_number"] = seq
        return super().create(vals_list)

    # ====================================================
    # Actions
    # ====================================================

    def action_draft(self):
        self.ensure_one()
        if self.state in ["submitted", "under_review", "approved", "rejected"]:
            raise ValidationError(
                _("Cannot return to Draft from non-draft state.")
            )
        self.write({"state": "draft"})

    def action_submit(self):
        """Submit the application for review.

        FR-01: Pre-onboarding scrutiny - validate compliance requirements before submission.
        """
        for record in self:
            if not record.document_ids:
                raise ValidationError(
                    _("Application must have at least one document.")
                )
            if not record.is_compliant:
                raise ValidationError(
                    _(
                        "Application is not compliant. Missing requirements: %(count)d"
                    ) % {"count": record.missing_requirements_count}
                )
            record.write({
                "state": "submitted",
                "submission_date": fields.Datetime.now(),
            })

    def action_ai_scrutiny(self):
        """Run AI document scrutiny.

        AI-01 to AI-07: Integration with AI document management system.
        """
        self.ensure_one()
        # Run AI validation via queue job for async processing
        self.with_delay(
            channel="alpha.ai.scrutiny",
            description=_("AI Document Scrutiny for %(name)s", name=self.name),
        )._run_ai_scrutiny()

    def _run_ai_scrutiny(self):
        """Internal method to run AI scrutiny asynchronously."""
        # This method would integrate with external AI service
        # For now, simulate AI processing
        import json
        import base64

        ai_results = {
            "completeness_score": 85.0,
            "validity_score": 92.0,
            "consistency_score": 78.0,
            "documents_checked": len(self.document_ids),
            "findings": [],
            "confidence_levels": [],
        }

        # Store AI results
        self.write({
            "ai_results_json": ai_results,
            "ai_scrutiny_summary": _("AI scrutiny completed. Score: 85%"),
            "state": "ai_scrutiny",
        })

    def action_fix_gaps(self):
        """Agency is fixing compliance gaps identified by AI."""
        self.write({"state": "agency_fixes"})

    def action_return_to_agency(self, reason=None):
        """Return application to agency with reasons."""
        self.ensure_one()
        self.write({
            "state": "returned",
            "return_reason": reason or _("Please review and correct the issues."),
        })

    def action_reject(self, reason=None):
        """Reject the application."""
        self.ensure_one()
        self.write({
            "state": "rejected",
            "rejection_reason": reason or _("Application rejected."),
        })

    def action_approve(self):
        """Approve the application."""
        self.ensure_one()
        self.write({
            "state": "approved",
            "approval_date": fields.Datetime.now(),
        })
        # Create approval signature request
        self._create_approval_signature()

    def action_create_approval(self):
        """Create approval signature request for signed decision letter."""
        self.ensure_one()
        self._create_approval_signature()

    # ====================================================
    # Signature Methods
    # ====================================================

    def _create_approval_signature(self):
        """Create digital signature request for approval letter."""
        self.ensure_one()
        if not self.sign_request_id:
            self.env["sign.oca.request"].create({
                "name": _("Approval for %(name)s", name=self.agency_id.name),
                "template_id": self.env.ref("sign_oca.sign_oca_template_approval").id,
                "data": b"",
                "filename": "approval_letter.pdf",
                "user_id": self.env.user.id,
                "record_ref": "alpha.agency.application,%s" % self.id,
                "company_id": self.company_id.id,
            })

    # ====================================================
    # Portal Methods
    # ====================================================

    def _compute_access_url(self):
        for record in self:
            record.access_url = f"/my/agency/application/{record.id}"

    @api.model
    def _get_portal_frontend_redirect_url(self, token):
        """Return URL for portal access."""
        return f"/my/agency/application/{self.id}"


class AgencyApplicationDocument(models.Model):
    """Documents submitted with agency application."""
    _name = "alpha.agency.application.document"
    _description = "Agency Application Document"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(
        string="Document Name",
        required=True,
        tracking=True,
    )
    application_id = fields.Many2one(
        comodel_name="alpha.agency.application",
        string="Application",
        ondelete="cascade",
        index=True,
        required=True,
    )
    file_id = fields.Many2one(
        comodel_name="dms.file",
        string="Document",
        ondelete="cascade",
        tracking=True,
    )
    required = fields.Boolean(
        string="Required",
        default=True,
    )
    description = fields.Text(
        string="Description",
    )
    upload_date = fields.Datetime(
        string="Upload Date",
        default=fields.Datetime.now,
        tracking=True,
    )
    ai_validated = fields.Boolean(
        string="AI Validated",
        readonly=True,
        tracking=True,
    )
    ai_comments = fields.Text(
        string="AI Comments",
        readonly=True,
    )
    officer_override = fields.Boolean(
        string="Officer Override",
        readonly=True,
        tracking=True,
    )
    # Compliance mapping
    mapping_id = fields.Many2one(
        comodel_name="alpha.compliance.requirement",
        string="Mapped Requirement",
        tracking=True,
        help="Map this document to a compliance requirement.",
    )
    company_id = fields.Many2one(
        "res.company",
        related="application_id.company_id",
        store=True,
        index=True,
        readonly=True,
    )

    @api.onchange("file_id")
    def _onchange_file_id(self):
        if self.file_id:
            self.name = self.file_id.name


class ComplianceRequirement(models.Model):
    """Compliance requirement model for pre-onboarding scrutiny (FR-01)."""
    _name = "alpha.compliance.requirement"
    _description = "Compliance Requirement"
    _order = "sequence, name"

    name = fields.Char(
        string="Requirement Name",
        required=True,
    )
    code = fields.Char(
        string="Code",
        required=True,
    )
    description = fields.Text(
        string="Description",
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )
    active = fields.Boolean(
        string="Active",
        default=True,
    )
    agency_type_ids = fields.Many2many(
        comodel_name="alpha.agency",
        relation="alpha_compliance_agency_type_rel",
        column1="compliance_requirement_id",
        column2="agency_type",
        string="Applicable Agency Types",
        domain="[('agency_type', '!=', False)]",
    )

    # Related documents
    document_ids = fields.One2many(
        comodel_name="alpha.agency.application.document",
        inverse_name="mapping_id",
        string="Mapped Documents",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )

    @api.constrains("code")
    def _check_code_unique(self):
        for record in self:
            existing = self.search([
                ("code", "=", record.code),
                ("id", "!=", record.id),
            ])
            if existing:
                raise ValidationError(
                    _("Compliance requirement code must be unique.")
                )


class ComplianceChecklist(models.Model):
    """Compliance checklist configuration (FR-06)."""
    _name = "alpha.compliance.checklist"
    _description = "Compliance Checklist"
    _order = "effective_date desc, name"

    name = fields.Char(
        string="Checklist Name",
        required=True,
    )
    code = fields.Char(
        string="Code",
        required=True,
    )
    description = fields.Text(
        string="Description",
    )
    active = fields.Boolean(
        string="Active",
        default=True,
    )
    requirement_ids = fields.Many2many(
        comodel_name="alpha.compliance.requirement",
        relation="alpha_checklist_requirement_rel",
        column1="checklist_id",
        column2="requirement_id",
        string="Requirements",
    )
    effective_date = fields.Date(
        string="Effective Date",
    )
    expiry_date = fields.Date(
        string="Expiry Date",
    )
    version = fields.Char(
        string="Version",
        default="1.0",
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )

    @api.constrains("code")
    def _check_code_unique(self):
        for record in self:
            existing = self.search([
                ("code", "=", record.code),
                ("effective_date", "<=", fields.Date.today()),
                ("id", "!=", record.id),
            ])
            if existing:
                raise ValidationError(
                    _("Active checklist with same code already exists.")
                )