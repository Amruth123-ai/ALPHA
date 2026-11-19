# Copyright 2026 Alpha Agency Lifecycle Platform
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "Alpha",
    "summary": "Agency Lifecycle Management Platform for Odoo Community",
    "version": "19.0.1.0.0",
    "category": "Extra Tools",
    "license": "LGPL-3",
    "author": "Odoo Community Agency Lifecycle Platform",
    "website": "https://github.com/OCA",
    "depends": [
        "base",
        "mail",
        "portal",
        "auth_signup",
        "dms",
        "sign_oca",
        "helpdesk_mgmt",
        "helpdesk_mgmt_activity",
        "helpdesk_mgmt_sla",
        "helpdesk_portal_priority",
        "helpdesk_ticket_partner_response",
        "helpdesk_ticket_related",
        "queue_job",
        "report_xlsx",
        "account",
        "account_invoice_auto_send_by_email",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/agency_data.xml",
        "views/agency_application_views.xml",
        "views/agency_audit_views.xml",
        "views/agency_device_views.xml",
        "views/agency_licence_views.xml",
        "views/agency_views.xml",
        "views/agency_workflow_views.xml",
        "views/compliance_views.xml",
        "views/credential_views.xml",
        "views/helpdesk_ticket_views.xml",
        "views/res_users_views.xml",
        "views/menus.xml",
        "views/portal/portal_templates.xml",
        
    ],

    "demo":
    [
            "data/demo_data.xml",
    ],

    "assets": {
        "web.assets_backend": [
            "alpha/static/src/js/alpha_backend.js",
        ],
        "web.assets_frontend": [
            "alpha/static/src/scss/alpha_portal.scss",
        ],
    },
    "application": True,
    "installable": True,
    "test": [
        "tests/test_agency_lifecycle.py",
    ],
}
