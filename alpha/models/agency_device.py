# Copyright 2026 Alpha Agency Lifecycle Platform
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError


class AgencyDevice(models.Model):
    """Device certification model (FR-13).

    Manages device vendors uploading certification documents and
    Testing Directorate recording testing/certification results.
    """
    _name = "alpha.agency.device"
    _description = "Agency Device"
    _inherit = ["mail.thread", "mail.activity.mixin", "portal.mixin"]
    _order = "create_date desc"

    # ====================================================
    # Core Fields
    # ====================================================

    name = fields.Char(
        string="Device Name",
        required=True,
        tracking=True,
    )
    device_code = fields.Char(
        string="Device Code",
        required=True,
        tracking=True,
    )
    manufacturer = fields.Char(
        string="Manufacturer",
        tracking=True,
    )
    model = fields.Char(
        string="Model",
        tracking=True,
    )
    serial_number = fields.Char(
        string="Serial Number",
        tracking=True,
    )

    company_id = fields.Many2one(
    "res.company",
    related="agency_id.company_id",
    store=True,
    index=True,
)
    # ====================================================
    # Agency Reference
    # ====================================================

    agency_id = fields.Many2one(
        comodel_name="alpha.agency",
        string="Agency (Vendor)",
        ondelete="restrict",
        index=True,
        required=True,
        tracking=True,
        domain="[('agency_type', 'in', ['type_c', 'type_a', 'type_b'])]",
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
    # Certification Status
    # ====================================================

    state = fields.Selection(
        selection=[
            ("pending", "Pending Submission"),
            ("submitted", "Submitted"),
            ("under_review", "Under Review"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("expired", "Expired"),
        ],
        string="Certification Status",
        default="pending",
        tracking=True,
    )
    certification_date = fields.Date(
        string="Certification Date",
        tracking=True,
    )
    expiry_date = fields.Date(
        string="Expiry Date",
        tracking=True,
    )
    testing_directorate_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Testing Directorate User",
        readonly=True,
        tracking=True,
    )

    # ====================================================
    # Documents and Evidence
    # ====================================================

    certification_document_ids = fields.One2many(
        comodel_name="dms.file",
        inverse_name="res_id",
        domain="[('res_model', '=', 'alpha.agency.device')]",
        string="Certification Documents",
    )
    testing_report_id = fields.Many2one(
        comodel_name="dms.file",
        string="Testing Report",
        ondelete="set null",
        tracking=True,
    )

    # ====================================================
    # Testing Details
    # ====================================================

    testing_result = fields.Selection(
        selection=[
            ("pass", "Pass"),
            ("fail", "Fail"),
            ("conditional", "Conditional"),
            ("pending", "Pending"),
        ],
        string="Testing Result",
        tracking=True,
    )
    testing_comments = fields.Text(
        string="Testing Comments",
        tracking=True,
    )
    test_date = fields.Date(
        string="Test Date",
        tracking=True,
    )
    tested_by = fields.Many2one(
        comodel_name="res.users",
        string="Tested By",
        domain="[('is_testing_directorate', '=', True)]",
        tracking=True,
    )

    # ====================================================
    # Related Records
    # ====================================================

    helpdesk_ticket_ids = fields.One2many(
        comodel_name="helpdesk.ticket",
        inverse_name="device_id",
        string="Helpdesk Tickets",
    )

    # ====================================================
    # Computed Fields
    # ====================================================

    is_expired = fields.Boolean(
        string="Expired",
        compute="_compute_is_expired",
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

    # ====================================================
    # Constraints
    # ====================================================

    @api.constrains("device_code", "agency_id")
    def _check_unique_device_per_agency(self):
        for record in self:
            existing = self.search([
                ("device_code", "=", record.device_code),
                ("agency_id", "=", record.agency_id.id),
                ("id", "!=", record.id),
            ])
            if existing:
                raise ValidationError(
                    _("Device code must be unique per agency.")
                )

    # ====================================================
    # Actions
    # ====================================================

    def action_submit(self):
        """Submit device for certification."""
        self.ensure_one()
        if not self.certification_document_ids:
            raise ValidationError(
                _("Must upload certification documents before submitting.")
            )
        self.write({"state": "submitted"})

    def action_test(self):
        """Mark device as under testing."""
        self.ensure_one()
        self.write({"state": "under_review"})

    def action_approve(self):
        """Approve device certification."""
        self.ensure_one()
        self.write({
            "state": "approved",
            "certification_date": fields.Date.today(),
        })

    def action_reject(self):
        """Reject device certification."""
        self.write({
            "state": "rejected",
            "reject_date": fields.Date.today(),
        })

    def action_expire(self):
        """Mark device certification as expired."""
        self.write({"state": "expired"})

    # ====================================================
    # Portal Methods
    # ====================================================

    def _compute_access_url(self):
        for record in self:
            record.access_url = f"/my/agency/device/{record.id}"


class DeviceTestingResult(models.Model):
    """Testing result details for device certification."""
    _name = "alpha.agency.device.testing.result"
    _description = "Device Testing Result"
    _order = "create_date desc"

    name = fields.Char(
        string="Test Name",
        required=True,
    )
    device_id = fields.Many2one(
        comodel_name="alpha.agency.device",
        string="Device",
        ondelete="cascade",
        index=True,
        required=True,
    )
    tester_id = fields.Many2one(
        comodel_name="res.users",
        string="Tester",
        domain="[('is_testing_directorate', '=', True)]",
        required=True,
    )
    test_date = fields.Date(
        string="Test Date",
        required=True,
    )
    result = fields.Selection(
        selection=[
            ("pass", "Pass"),
            ("fail", "Fail"),
            ("partial", "Partial"),
            ("na", "Not Applicable"),
        ],
        string="Result",
        required=True,
    )
    comments = fields.Text(
        string="Comments",
    )
    evidence_file_id = fields.Many2one(
        comodel_name="dms.file",
        string="Evidence",
        ondelete="set null",
    )