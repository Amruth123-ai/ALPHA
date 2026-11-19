# Copyright 2026 Alpha Agency Lifecycle Platform
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import http
from odoo.http import request
import logging


_logger = logging.getLogger(__name__)


class AlphaPortalController(http.Controller):
    """Controller for agency portal self-service (FR-02)."""

    # ====================================================
    # Agency Portal Routes
    # ====================================================

    @http.route(['/my/agency'], type='http', auth='user', website=True)
    def my_agencies(self, **kw):
        """List all agencies related to the current user."""
        Agencies = request.env['alpha.agency'].sudo()
        # Get agencies where user is authorized or linked via partner
        agencies = Agencies.search([
            ('user_ids', 'in', request.env.user.id),
        ])
        # Also get through partner relationship
        partner_agencies = Agencies.search([
            ('partner_id.user_ids', 'in', request.env.user.id),
        ])
        all_agencies = agencies | partner_agencies

        return request.render('alpha.portal_my_agencies', {
            'agencies': all_agencies,
            'page_name': 'my_agencies',
        })

    @http.route(['/my/agency/<int:agency_id>'], type='http', auth='user', website=True)
    def agency_details(self, agency_id, **kw):
        """Show details of a specific agency."""
        Agency = request.env['alpha.agency'].sudo()
        agency = Agency.browse(agency_id)

        if not agency.exists():
            return request.not_found()

        # Check access rights
        if not self._check_agency_access_rights(agency):
            return request.render('alpha.portal_access_denied', {
                'agency': agency,
            })

        return request.render('alpha.portal_agency_details', {
            'agency': agency,
            'documents': agency.document_ids,
            'audits': agency.audit_ids,
            'licences': agency.licence_ids,
            'devices': agency.device_ids,
        })

    @http.route(['/my/agency/<model:agency>:/documents'], type='http', auth='user', website=True)
    def agency_documents(self, agency, **kw):
        """List documents for an agency."""
        agency = agency.sudo()
        return request.render('alpha.portal_agency_documents', {
            'agency': agency,
            'documents': agency.document_ids,
        })

    @http.route(['/my/agency/<model:agency>:/audits'], type='http', auth='user', website=True)
    def agency_audits(self, agency, **kw):
        """List audits for an agency."""
        agency = agency.sudo()
        return request.render('alpha.portal_agency_audits', {
            'agency': agency,
            'audits': agency.audit_ids,
        })

    @http.route(['/my/agency/<model:agency>:/licences'], type='http', auth='user', website=True)
    def agency_licences(self, agency, **kw):
        """List licences for an agency."""
        agency = agency.sudo()
        return request.render('alpha.portal_agency_licences', {
            'agency': agency,
            'licences': agency.licence_ids,
        })

    @http.route(['/my/agency/<model:agency>:/devices'], type='http', auth='user', website=True)
    def agency_devices(self, agency, **kw):
        """List devices for an agency."""
        agency = agency.sudo()
        return request.render('alpha.portal_agency_devices', {
            'agency': agency,
            'devices': agency.device_ids,
        })

    # ====================================================
    # Application Portal Routes
    # ====================================================

    @http.route(['/my/agency/application/<int:application_id>'], type='http', auth='user', website=True)
    def application_details(self, application_id, **kw):
        """Show details of an agency application."""
        Application = request.env['alpha.agency.application'].sudo()
        application = Application.browse(application_id)

        if not application.exists():
            return request.not_found()

        if not self._check_application_access_rights(application):
            return request.render('alpha.portal_access_denied', {
                'application': application,
            })

        return request.render('alpha.portal_application_details', {
            'application': application,
            'agency': application.agency_id,
            'documents': application.document_ids,
            'compliance_requirements': application.compliance_requirement_ids,
        })

    # ====================================================
    # Audit Portal Routes
    # ====================================================

    @http.route(['/my/agency/audit/<int:audit_id>'], type='http', auth='user', website=True)
    def audit_details(self, audit_id, **kw):
        """Show details of an agency audit."""
        Audit = request.env['alpha.agency.audit'].sudo()
        audit = Audit.browse(audit_id)

        if not audit.exists():
            return request.not_found()

        return request.render('alpha.portal_audit_details', {
            'audit': audit,
            'agency': audit.agency_id,
            'findings': audit.finding_ids,
            'corrective_actions': audit.corrective_action_ids,
            'evidence': audit.evidence_ids,
        })

    # ====================================================
    # Licence Portal Routes
    # ====================================================

    @http.route(['/my/agency/licence/<int:licence_id>'], type='http', auth='user', website=True)
    def licence_details(self, licence_id, **kw):
        """Show details of an agency licence."""
        Licence = request.env['alpha.agency.licence'].sudo()
        licence = Licence.browse(licence_id)

        if not licence.exists():
            return request.not_found()

        return request.render('alpha.portal_licence_details', {
            'licence': licence,
            'agency': licence.agency_id,
            'documents': licence.document_ids,
        })

    # ====================================================
    # Document Upload Routes
    # ====================================================

    @http.route(['/my/agency/upload_document'], type='http', auth='user', website=True, methods=['POST'])
    def upload_document(self, **kw):
        """Handle document upload from portal."""
        # This would handle file uploads via DMS
        # Implementation depends on DMS module configuration
        return request.redirect('/my/agency')

    # ====================================================
    # Helper Methods
    # ====================================================

    def _check_agency_access_rights(self, agency):
        """Check if current user has access to view the agency."""
        user = request.env.user
        # User is authorized or agency is related to user's partner
        return (
            agency.user_ids.contains(user) or
            agency.partner_id.user_ids.contains(user) or
            user.has_group('alpha.group_alpha_agency_manager')
        )

    def _check_application_access_rights(self, application):
        """Check if current user has access to view the application."""
        user = request.env.user
        return (
            application.agency_id.user_ids.contains(user) or
            application.agency_id.partner_id.user_ids.contains(user) or
            user.has_group('alpha.group_alpha_agency_manager')
        )