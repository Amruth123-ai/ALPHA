# Copyright 2026 Alpha Agency Lifecycle Platform
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError


class Agency(models.Model):
    """Core Agency model representing an agency in the lifecycle management platform.

    Supports five agency types:
    - Type A: User Agency
    - Type B: KYC User Agency
    - Type C: Service Provider Agency
    - Type D: Sub-user Agency
    - Type E: Sub-KYC User Agency
    """
    _name = "alpha.agency"
    _description = "Agency"
    _inherit = ["mail.thread", "mail.activity.mixin", "portal.mixin"]
    _order = "create_date desc"

    # ====================================================
    # Core Fields
    # ====================================================

    name = fields.Char(
        string="Agency Name",
        required=True,
        copy=False,
        tracking=True,
    )
    code = fields.Char(
        string="Agency Code",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: "/",
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("pending", "Pending Approval"),
            ("approved", "Approved"),
            ("in_production", "In Production"),
            ("suspended", "Suspended"),
            ("deboarded", "Deboarded"),
            ("archived", "Archived"),
        ],
        string="Status",
        default="draft",
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
        required=True,
        tracking=True,
    )
    description = fields.Html(
        string="Description",
        sanitize_style=True,
    )
    is_locked = fields.Boolean(
        string="Locked",
        help="If checked, the agency cannot be modified.",
        tracking=True,
    )

    # ====================================================
    # Partner/Organization Relations
    # ====================================================

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        ondelete="restrict",
        index=True,
        tracking=True,
        help="Linked partner for this agency.",
    )
    primary_contact_id = fields.Many2one(
        comodel_name="res.partner",
        string="Primary Contact",
        domain="[('is_company', '=', True)]",
        tracking=True,
    )
    parent_agency_id = fields.Many2one(
        comodel_name="alpha.agency",
        string="Parent Agency",
        ondelete="set null",
        index=True,
        help="Parent agency for sub-agencies.",
    )
    child_agency_ids = fields.One2many(
        comodel_name="alpha.agency",
        inverse_name="parent_agency_id",
        string="Child Agencies",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )
    organizational_unit = fields.Selection(
        selection=[
            ("ho", "Head Office (HO)"),
            ("ro", "Regional Office (RO)"),
            ("tc", "Technical Centre (TC)"),
        ],
        string="Organizational Unit",
        default="ho",
        required=True,
        tracking=True,
    )

    # ====================================================
    # Contact Information
    # ====================================================

    email = fields.Char(
        string="Email",
        tracking=True,
    )
    phone = fields.Char(
        string="Phone",
        tracking=True,
    )
    website = fields.Char(
        string="Website",
        tracking=True,
    )
    address = fields.Char(
        string="Address",
        tracking=True,
    )
    city = fields.Char(
        string="City",
        tracking=True,
    )
    state_id = fields.Many2one(
        comodel_name="res.country.state",
        string="State",
        tracking=True,
    )
    country_id = fields.Many2one(
        comodel_name="res.country",
        string="Country",
        tracking=True,
    )
    zip_code = fields.Char(
        string="ZIP Code",
        tracking=True,
    )

    # ====================================================
    # Related Records
    # ====================================================

    application_id = fields.Many2one(
        comodel_name="alpha.agency.application",
        string="Application",
        readonly=True,
        ondelete="set null",
    )
    user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="alpha_agency_user_rel",
        column1="agency_id",
        column2="user_id",
        string="Authorized Users",
    )
    document_ids = fields.One2many(
        comodel_name="dms.file",
        inverse_name="res_id",
        domain="[('res_model', '=', 'alpha.agency')]",
        string="Documents",
    )
    ticket_ids = fields.One2many(
        comodel_name="helpdesk.ticket",
        inverse_name="alpha_agency_id",
        string="Helpdesk Tickets",
    )
    audit_ids = fields.One2many(
        comodel_name="alpha.agency.audit",
        inverse_name="agency_id",
        string="Audits",
    )
    licence_ids = fields.One2many(
        comodel_name="alpha.agency.licence",
        inverse_name="agency_id",
        string="Licences",
    )
    device_ids = fields.One2many(
        comodel_name="alpha.agency.device",
        inverse_name="agency_id",
        string="Devices",
    )

    # ====================================================
    # Computed Fields
    # ====================================================

    active_document_count = fields.Integer(
        string="Active Documents",
        compute="_compute_active_document_count",
        store=False,
    )
    audit_count = fields.Integer(
        string="Total Audits",
        compute="_compute_audit_counts",
        store=False,
    )
    pending_audit_count = fields.Integer(
        string="Pending Audits",
        compute="_compute_audit_counts",
        store=False,
    )

    # ====================================================
    # Computation Methods
    # ====================================================

    @api.depends("document_ids")
    def _compute_active_document_count(self):
        for record in self:
            record.active_document_count = len(
                record.document_ids.filtered(lambda d: d.active)
            )

    @api.depends("audit_ids.state")
    def _compute_audit_counts(self):
        for record in self:
            audits = record.audit_ids
            record.audit_count = len(audits)
            record.pending_audit_count = len(
                audits.filtered(lambda a: a.state not in ["closed", "cancelled"])
            )

    # ====================================================
    # Onchange Methods
    # ====================================================

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id:
            self.name = self.partner_id.name
            self.email = self.partner_id.email or False
            self.phone = self.partner_id.phone or False
            self.website = self.partner_id.website or False
            if self.partner_id.street:
                self.address = self.partner_id.street
            if self.partner_id.city:
                self.city = self.partner_id.city
            if self.partner_id.state_id:
                self.state_id = self.partner_id.state_id.id
            if self.partner_id.country_id:
                self.country_id = self.partner_id.country_id.id
            if self.partner_id.zip:
                self.zip_code = self.partner_id.zip

    # ====================================================
    # Constraints
    # ====================================================

    _sql_constraints = [
        (
            "code_unique",
            "UNIQUE(code)",
            "Agency code must be unique.",
        ),
    ]

    @api.constrains("parent_agency_id")
    def _check_parent_agency(self):
        for record in self:
            if record.parent_agency_id == record:
                raise ValidationError(
                    _("An agency cannot be its own parent.")
                )
            if record.parent_agency_id and record.parent_agency_id.state == "draft":
                raise ValidationError(
                    _("Cannot link to a draft agency.")
                )

    # ====================================================
    # Override Methods
    # ====================================================

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("code", "/") == "/":
                seq = self.env["ir.sequence"].next_by_code("alpha.agency")
                vals["code"] = seq or vals.get("name", "NEW").upper().replace(" ", "_")
        return super().create(vals_list)

    def write(self, vals):
        if self.is_locked:
            raise AccessError(
                _("This agency is locked and cannot be modified.")
            )
        if "state" in vals and vals.get("state") == "draft" and self.state != "draft":
            if self.application_id:
                raise ValidationError(
                    _("Cannot change state to Draft if there is an active application.")
                )
        return super().write(vals)

    # ====================================================
    # Actions
    # ====================================================

    def action_draft(self):
        self.ensure_one()
        if self.audit_ids.filtered(lambda a: a.state not in ["closed", "cancelled"]):
            raise ValidationError(
                _("Cannot set to Draft with open audits.")
            )
        self.write({"state": "draft"})

    def action_approve(self):
        """Approve the agency and create the application."""
        self.ensure_one()
        self.write({"state": "approved"})
        # Create application for new agencies
        if not self.application_id:
            self.env["alpha.agency.application"].create({
                "agency_id": self.id,
                "state": "draft",
            })

    def action_in_production(self):
        """Move agency to production status."""
        self.ensure_one()
        if not self.application_id or self.application_id.state != "approved":
            raise ValidationError(
                _("Agency must have an approved application before production.")
            )
        self.write({"state": "in_production"})

    def action_suspend(self, reason=None):
        """Suspend the agency."""
        self.ensure_one()
        self.write({
            "state": "suspended",
            "is_locked": True,
        })
        # Lock all related records
        self._lock_related_records()

    def action_deboard(self, reason=None):
        """Deboard the agency - mark as archived but keep searchable."""
        self.ensure_one()
        self.write({
            "state": "deboarded",
            "is_locked": True,
        })
        # Archive all related documents
        self._archive_related_documents()

    def action_archive(self):
        """Archive the agency - searchable archived state."""
        self.ensure_one()
        self.write({"state": "archived"})

    def action_unlock(self):
        """Unlock the agency for modifications."""
        self.ensure_one()
        self.write({"is_locked": False})

    # ====================================================
    # Helper Methods
    # ====================================================

    def _lock_related_records(self):
        """Lock all related records when agency is suspended."""
        self.audit_ids.write({"is_locked": True})
        self.licence_ids.write({"is_locked": True})

    def _archive_related_documents(self):
        """Archive all related DMS documents when agency is deboarded."""
        documents = self.document_ids.filtered(lambda d: d.active)
        if documents:
            documents.write({"active": False})

    # ====================================================
    # Portal Methods
    # ====================================================

    def _compute_access_url(self):
        for record in self:
            record.access_url = f"/my/agency/{record.id}"

    @api.model
    def _get_portal_frontend_redirect_url(self, token):
        """Return URL for portal access."""
        return f"/my/agency/{self.id}"