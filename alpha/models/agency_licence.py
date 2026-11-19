# Copyright 2026 Alpha Agency Lifecycle Platform
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError


class AgencyLicence(models.Model):
    """Licence and credentials model (FR-10).

    Manages agency licences, credentials, permits, and certificates
    with their types, validity periods, and issuance status.
    """
    _name = "alpha.agency.licence"
    _description = "Agency Licence"
    _inherit = ["mail.thread", "mail.activity.mixin", "portal.mixin"]
    _order = "validity_date desc, create_date"

    # ====================================================
    # Core Fields
    # ====================================================

    name = fields.Char(
        string="Licence Name",
        required=True,
        tracking=True,
    )
    licence_number = fields.Char(
        string="Licence Number",
        tracking=True,
    )
    licence_type = fields.Selection(
        selection=[
            ("general_license", "General Licence"),
            ("business_license", "Business License"),
            ("certificate_of_authorization", "Certificate of Authorization"),
            ("accreditation", "Accreditation Certificate"),
            ("permit", "Permit"),
            ("registration", "Registration"),
            ("other", "Other"),
        ],
        string="Licence Type",
        required=True,
        tracking=True,
    )
    description = fields.Text(
        string="Description",
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
        domain="[('state', 'in', ['approved', 'in_production', 'suspended'])]",
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

    company_id = fields.Many2one(
    "res.company",
    related="agency_id.company_id",
    store=True,
    index=True,
)

    # ====================================================
    # Validity and Status
    # ====================================================

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("issued", "Issued"),
            ("active", "Active"),
            ("suspended", "Suspended"),
            ("cancelled", "Cancelled"),
            ("expired", "Expired"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )
    issue_date = fields.Date(
        string="Issue Date",
        tracking=True,
    )
    expiry_date = fields.Date(
        string="Expiry Date",
        tracking=True,
    )
    validity_date = fields.Date(
        string="Validity Date",
        tracking=True,
        help="Date until which the licence is valid.",
    )
    renewal_reminder_days = fields.Integer(
        string="Renewal Reminder (Days)",
        default=30,
        tracking=True,
        help="Number of days before expiry to send renewal reminder.",
    )

    # ====================================================
    # Issuing Authority
    # ====================================================

    issuing_authority_id = fields.Many2one(
        comodel_name="res.users",
        string="Issuing Authority",
        domain="[('is_licensing_officer', '=', True)]",
        tracking=True,
    )
    issuing_office = fields.Char(
        string="Issuing Office",
        tracking=True,
    )
    license_key = fields.Char(
        string="License Key",
        tracking=True,
    )

    # ====================================================
    # Documents and Evidence
    # ====================================================

    document_ids = fields.One2many(
        comodel_name="dms.file",
        inverse_name="res_id",
        domain="[('res_model', '=', 'alpha.agency.licence'), ('is_licence_doc', '=', True)]",
        string="Licence Documents",
    )
    original_document_id = fields.Many2one(
        comodel_name="dms.file",
        string="Original Document",
        ondelete="set null",
        tracking=True,
    )
    copy_document_id = fields.Many2one(
        comodel_name="dms.file",
        string="Copy Document",
        ondelete="set null",
    )

    # ====================================================
    # Related Records
    # ====================================================

    helpdesk_ticket_ids = fields.One2many(
        comodel_name="helpdesk.ticket",
        inverse_name="licence_id",
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

    is_expired = fields.Boolean(
        string="Expired",
        compute="_compute_is_expired",
        store=True,
    )
    is_expiring_soon = fields.Boolean(
        string="Expiring Soon",
        compute="_compute_expiring_soon",
        store=True,
    )
    days_to_expiry = fields.Integer(
        string="Days to Expiry",
        compute="_compute_days_to_expiry",
        store=True,
    )

    # ====================================================
    # Computation Methods
    # ====================================================

    @api.depends("expiry_date")
    def _compute_is_expired(self):
        for record in self:
            if record.expiry_date:
                record.is_expired = record.expiry_date < fields.Date.today()
            else:
                record.is_expired = False

    @api.depends("expiry_date", "renewal_reminder_days")
    def _compute_expiring_soon(self):
        for record in self:
            if record.expiry_date and record.renewal_reminder_days:
                today = fields.Date.today()
                reminder_date = fields.Date.to_string(
                    fields.Date.from_string(record.expiry_date) -
                    __import__('datetime').timedelta(days=record.renewal_reminder_days)
                )
                record.is_expiring_soon = today >= reminder_date and not record.is_expired
            else:
                record.is_expiring_soon = False

    @api.depends("expiry_date")
    def _compute_days_to_expiry(self):
        for record in self:
            if record.expiry_date:
                today = fields.Date.today()
                expiry = fields.Date.from_string(record.expiry_date)
                delta = expiry - today
                record.days_to_expiry = delta.days
            else:
                record.days_to_expiry = 0

    # ====================================================
    # Constraints
    # ====================================================

    @api.constrains("expiry_date", "issue_date")
    def _check_validity_dates(self):
        for record in self:
            if record.issue_date and record.expiry_date:
                if record.expiry_date < record.issue_date:
                    raise ValidationError(
                        _("Expiry date cannot be before issue date."))

    @api.constrains("licence_number", "agency_id")
    def _check_unique_licence_per_agency(self):
        for record in self:
            if record.licence_number:
                existing = self.search([
                    ("licence_number", "=", record.licence_number),
                    ("agency_id", "=", record.agency_id.id),
                    ("state", "not in", ["cancelled"]),
                    ("id", "!=", record.id),
                ])
                if existing:
                    raise ValidationError(
                        _("Licence number must be unique per agency."))

    # ====================================================
    # Override Methods
    # ====================================================

    @api.model
    def create(self, vals):
        return super().create(vals)

    def write(self, vals):
        # Auto-set issue date when moving to active/issued
        if vals.get("state") in ["issued", "active"] and not self.issue_date:
            vals["issue_date"] = fields.Date.today()
        return super().write(vals)

    # ====================================================
    # Actions
    # ====================================================

    def action_draft(self):
        """Set licence to draft state."""
        self.write({"state": "draft"})

    def action_issue(self):
        """Issue the licence."""
        for record in self:
            if not record.agency_id:
                raise ValidationError(
                    _("Cannot issue licence without agency."))
            if not record.issue_date:
                record.issue_date = fields.Date.today()
            record.write({"state": "issued"})
            # Schedule for activation
            record.with_delay(
                channel="alpha.licence.cron",
                description=_("Activate licence %(name)s", name=record.name),
            ).action_activate()

    def action_activate(self):
        """Activate the licence."""
        self.write({"state": "active"})
        # Create digital signature
        self._create_signature()

    def action_suspend(self):
        """Suspend the licence."""
        self.write({"state": "suspended"})

    def action_cancel(self):
        """Cancel the licence."""
        self.write({"state": "cancelled"})

    def action_expire(self):
        """Mark licence as expired."""
        self.write({
            "state": "expired",
            "validity_date": fields.Date.today(),
        })

    def action_renew(self):
        """Renew the licence."""
        self.ensure_one()
        if self.state != "expired":
            raise ValidationError(
                _("Only expired licences can be renewed."))
        view = self.env.ref("alpha.view_alpha_agency_licence_form")
        return {
            "type": "ir.actions.act_window",
            "name": _("Renew Licence - %(name)s" % {"name": self.name}),
            "view_mode": "form",
            "view_id": view.id,
            "target": "new",
            "context": {
                "default_agency_id": self.agency_id.id,
                "default_licence_number": self.licence_number,
                "default_validity_date": fields.Date.today(),
            }
        }

    # ====================================================
    # Signature Methods
    # ====================================================

    def _create_signature(self):
        """Create digital signature request for the licence."""
        self.ensure_one()
        if not self.sign_request_id:
            self.env["sign.oca.request"].create({
                "name": _("Licence Signature - %(name)s", name=self.name),
                "template_id": self.env.ref("sign_oca.sign_oca_template_licence").id,
                "data": b"",
                "filename": "licence_%s.pdf" % self.licence_number or "licence.pdf",
                "user_id": self.issuing_authority_id.id or self.env.user.id,
                "record_ref": "alpha.agency.licence,%s" % self.id,
                "company_id": self.company_id.id,
            })

    # ====================================================
    # Notification Methods
    # ====================================================

    def _send_renewal_notification(self):
        """Send renewal notification to agency."""
        for record in self.filtered("is_expiring_soon"):
            template = self.env.ref("alpha.mail_template_licence_renewal")
            if template:
                template.send_mail(record.id, force_send=True)

    # ====================================================
    # Portal Methods
    # ====================================================

    def _compute_access_url(self):
        for record in self:
            record.access_url = f"/my/agency/licence/{record.id}"


class AgencyCredential(models.Model):
    """Credentials model for additional agency credentials (FR-10)."""
    _name = "alpha.agency.credential"
    _description = "Agency Credential"
    _order = "create_date desc"

    name = fields.Char(
        string="Credential Name",
        required=True,
        tracking=True,
    )
    credential_code = fields.Char(
        string="Credential Code",
        tracking=True,
    )
    agency_id = fields.Many2one(
        comodel_name="alpha.agency",
        string="Agency",
        ondelete="cascade",
        index=True,
        required=True,
    )
    credential_type = fields.Selection(
        selection=[
            ("training", "Training Certificate"),
            ("certification", "Professional Certification"),
            ("permit", "Work Permit"),
            ("clearance", "Security Clearance"),
            ("membership", "Professional Membership"),
            ("other", "Other"),
        ],
        string="Credential Type",
        required=True,
        tracking=True,
    )
    issuing_organization = fields.Char(
        string="Issuing Organization",
        tracking=True,
    )
    issue_date = fields.Date(
        string="Issue Date",
        tracking=True,
    )
    expiry_date = fields.Date(
        string="Expiry Date",
        tracking=True,
    )
    document_id = fields.Many2one(
        comodel_name="dms.file",
        string="Credential Document",
        ondelete="set null",
        tracking=True,
    )
    is_valid = fields.Boolean(
        string="Valid",
        compute="_compute_is_valid",
        store=True,
    )

    @api.depends("expiry_date")
    def _compute_is_valid(self):
        for record in self:
            if record.expiry_date:
                record.is_valid = record.expiry_date >= fields.Date.today()
            else:
                record.is_valid = True