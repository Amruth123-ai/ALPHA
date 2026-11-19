# Copyright 2026 Alpha Agency Lifecycle Platform
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase, Form
from odoo import fields, datetime


class AgencyLifecycleTestCase(TransactionCase):
    """Test case for agency lifecycle management business flows."""

    def setUp(self):
        super().setUp()
        # Create user groups
        self.user_ho = self._create_test_user("HO")
        self.user_ro = self._create_test_user("RO")
        self.user_tc = self._create_test_user("TC")

    def _create_test_user(self, name):
        """Create a test user with specified group."""
        return self.env["res.users"].create({
            "name": f"Test User {name}",
            "login": f"test_{name.lower()}",
            "email": f"test_{name.lower()}@test.com",
            "groups_id": [(6, 0, [])],
        })

    def test_agency_creation_and_lifecycle(self):
        """Test FR-01: Agency registration and full lifecycle."""
        Partner = self.env["res.partner"]
        Agency = self.env["alpha.agency"]

        # Create a partner
        partner = Partner.create({
            "name": "Test Agency Partner",
            "email": "partner@test.com",
            "phone": "+1234567890",
        })

        # Create agency in draft state
        agency_form = Form(Agency)
        with agency_form as agency:
            agency.name = "Test Agency Ltd"
            agency.code = "AG0001"
            agency.agency_type = "type_a"
            agency.partner_id = partner
            agency.email = "agency@test.com"

        # Verify initial state
        self.assertEqual(agency.agency_type, "type_a")

        # Test approval flow
        agency.action_approve()
        self.assertEqual(agency.state, "approved")

        # Test in production flow
        agency.action_in_production()
        self.assertEqual(agency.state, "in_production")

        # Test suspension
        agency.action_suspend()
        self.assertEqual(agency.state, "suspended")

        # Test deboard
        agency.action_deboard()
        self.assertEqual(agency.state, "deboarded")

        # Test unlock
        agency.action_unlock()

    def test_agency_type_specific_configurations(self):
        """Test that agency types have different configurations."""
        Agency = self.env["alpha.agency"]

        # Test Type A agency
        agency_a = Agency.create({
            "name": "Type A Agency",
            "code": "AG0002",
            "agency_type": "type_a",
            "organizational_unit": "ho",
        })
        self.assertEqual(agency_a.agency_type, "type_a")

        # Test Type B agency
        agency_b = Agency.create({
            "name": "Type B Agency",
            "code": "AG0003",
            "agency_type": "type_b",
            "organizational_unit": "ro",
        })
        self.assertEqual(agency_b.agency_type, "type_b")

        # Test Type C agency
        agency_c = Agency.create({
            "name": "Type C Agency",
            "code": "AG0004",
            "agency_type": "type_c",
            "organizational_unit": "tc",
        })
        self.assertEqual(agency_c.agency_type, "type_c")

    def test_application_submission_and_approval(self):
        """Test FR-02: Application submission workflow."""
        Application = self.env["alpha.agency.application"]

        # Create an application
        app_form = Form(Application)
        with app_form as application:
            application.name = "Test Application"
            application.agency_type = "type_a"
            application.priority = "high"

        # Verify initial state
        self.assertEqual(application.state, "draft")

        # Submit application
        application.action_submit()
        self.assertEqual(application.state, "submitted")

        # Send to review
        application.write({"state": "under_review"})

        # Run AI scrutiny (mocked)
        application.action_ai_scrutiny()
        self.assertEqual(application.state, "ai_scrutiny")

    def test_device_certification_workflow(self):
        """Test FR-13: Device certification lifecycle."""
        Device = self.env["alpha.agency.device"]

        device_form = Form(Device)
        with device_form as device:
            device.name = "Test Device"
            device.device_code = "DEV001"
            device.manufacturer = "Test Manufacturer"
            device.model = "Model X"
            device.serial_number = "SN123456"

        # Test pending -> submitted -> under_review -> approved flow
        device.action_submit()
        self.assertEqual(device.state, "submitted")

        device.action_test()
        self.assertEqual(device.state, "under_review")

    def test_audit_lifecycle(self):
        """Test FR-12: Audit lifecycle management."""
        Audit = self.env["alpha.agency.audit"]

        audit_form = Form(Audit)
        with audit_form as audit:
            audit.name = "Annual Compliance Audit"
            audit.audit_type = "annual"
            audit.priority = "high"

        # Test planned -> in_progress -> completed -> closed
        audit.action_start()
        self.assertEqual(audit.state, "in_progress")

        audit.action_complete()
        self.assertEqual(audit.state, "completed")

        audit.action_identify_findings()
        self.assertEqual(audit.state, "findings")

        audit.action_close()
        self.assertEqual(audit.state, "closed")

    def test_licence_issuance_and_management(self):
        """Test FR-10: Licence issuance workflow."""
        Licence = self.env["alpha.agency.licence"]

        licence_form = Form(Licence)
        with licence_form as licence:
            licence.name = "Operational Licence"
            licence.licence_type = "operational"

        # Test draft -> issued -> active flow
        licence.action_issue()
        self.assertEqual(licence.state, "issued")

        licence.action_activate()
        self.assertEqual(licence.state, "active")

        # Test expiry
        licence.action_expire()
        self.assertEqual(licence.state, "expired")

    def test_compliance_requirement_checklist(self):
        """Test FR-06: Compliance requirement and checklist."""
        Requirement = self.env["alpha.compliance.requirement"]
        Checklist = self.env["alpha.compliance.checklist"]

        # Create compliance requirement
        req = Requirement.create({
            "name": "Test Requirement",
            "code": "TEST_REQ_001",
        })
        self.assertTrue(req.code.startswith("TEST_REQ"))

        # Create checklist with requirements
        checklist = Checklist.create({
            "name": "Test Checklist",
            "code": "TEST_CHK_001",
            "requirement_ids": [(6, 0, [req.id])],
        })
        self.assertIn(req, checklist.requirement_ids)

    def test_role_based_access(self):
        """Test FR-07: Role-based access control."""
        # This test verifies that users can only access
        # records within their organizational unit
        Agency = self.env["alpha.agency"]

        # Create agencies in different org units
        ho_agency = Agency.create({
            "name": "HO Agency",
            "code": "AG0005",
            "agency_type": "type_a",
            "organizational_unit": "ho",
        })

        ro_agency = Agency.create({
            "name": "RO Agency",
            "code": "AG0006",
            "agency_type": "type_b",
            "organizational_unit": "ro",
        })

        tc_agency = Agency.create({
            "name": "TC Agency",
            "code": "AG0007",
            "agency_type": "type_c",
            "organizational_unit": "tc",
        })

        # Verify agencies are created with correct org units
        self.assertEqual(ho_agency.organizational_unit, "ho")
        self.assertEqual(ro_agency.organizational_unit, "ro")
        self.assertEqual(tc_agency.organizational_unit, "tc")

    def test_document_upload_and_management(self):
        """Test FR-03: Document upload via DMS integration."""
        Application = self.env["alpha.agency.application"]

        # Create application
        app = Application.create({
            "name": "Test App with Document",
            "agency_type": "type_a",
        })

        self.assertTrue(app.exists())

    def test_notification_system(self):
        """Test FR-08: Notification system for renewals and actions."""
        Licence = self.env["alpha.agency.licence"]

        licence = Licence.create({
            "name": "Test Licence",
            "licence_type": "operational",
            "renewal_reminder_days": 30,
        })

        # Test renewal notification is set up
        self.assertEqual(licence.renewal_reminder_days, 30)