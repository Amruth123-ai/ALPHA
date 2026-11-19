# Copyright 2026 Alpha Agency Lifecycle Platform
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models
from odoo.tools import safe_eval


class AgencyMISReport(models.AbstractModel):
    """MIS Report for Agency Management Dashboard."""
    _name = "report.alpha.agency_mis_report"
    _description = "Agency MIS Report"

    def _get_report_values(self, docids, data=None):
        """Generate report data for MIS dashboard."""
        report_data = {
            "total_agencies": self.env["alpha.agency"].search_count([]),
            "agencies_by_type": self._get_agencies_by_type(),
            "agencies_by_state": self._get_agencies_by_state(),
            "applications_by_type": self._get_applications_by_type(),
            "applications_by_state": self._get_applications_by_state(),
            "devices_by_type": self._get_devices_by_type(),
            "devices_by_state": self._get_devices_by_state(),
            "licences_by_type": self._get_licences_by_type(),
            "licences_by_state": self._get_licences_by_state(),
            "upcoming_expiry": self._get_upcoming_expiry(),
        }
        return {
            "doc_ids": docids,
            "doc_model": "alpha.agency",
            "data": data,
            "report_data": report_data,
        }

    def _get_agencies_by_type(self):
        """Get agency counts by type."""
        types = ["type_a", "type_b", "type_c", "type_d", "type_e"]
        result = {}
        for t in types:
            count = self.env["alpha.agency"].search_count([("agency_type", "=", t)])
            result[t.replace("type_", "Type ").upper()] = count
        return result

    def _get_agencies_by_state(self):
        """Get agency counts by state."""
        states = ["draft", "pending", "approved", "in_production", "suspended", "deboarded"]
        result = {}
        for s in states:
            count = self.env["alpha.agency"].search_count([("state", "=", s)])
            result[s.replace("_", " ").title()] = count
        return result

    def _get_applications_by_type(self):
        """Get application counts by type."""
        types = ["type_a", "type_b", "type_c", "type_d", "type_e"]
        result = {}
        for t in types:
            count = self.env["alpha.agency.application"].search_count([("agency_type", "=", t)])
            result[t.replace("type_", "Type ").upper()] = count
        return result

    def _get_applications_by_state(self):
        """Get application counts by state."""
        states = ["draft", "submitted", "pending_approval", "approved", "rejected"]
        result = {}
        for s in states:
            count = self.env["alpha.agency.application"].search_count([("state", "=", s)])
            result[s.replace("_", " ").title()] = count
        return result

    def _get_devices_by_type(self):
        """Get device counts by manufacturer type."""
        manufacturers = self.env["alpha.agency.device"].search_groupby(
            "manufacturer", fields=["id"]
        )
        result = {}
        for m in manufacturers:
            result[m.manufacturer] = len(m.ids)
        return result

    def _get_devices_by_state(self):
        """Get device counts by certification state."""
        states = ["pending", "submitted", "under_review", "approved", "rejected"]
        result = {}
        for s in states:
            count = self.env["alpha.agency.device"].search_count([("state", "=", s)])
            result[s.replace("_", " ").title()] = count
        return result

    def _get_licences_by_type(self):
        """Get licence counts by type."""
        types = ["operational", "technical", "specialist", "other"]
        result = {}
        for t in types:
            count = self.env["alpha.agency.licence"].search_count([("licence_type", "=", t)])
            result[t.replace("_", " ").title()] = count
        return result

    def _get_licences_by_state(self):
        """Get licence counts by state."""
        states = ["draft", "issued", "active", "suspended", "expired", "cancelled"]
        result = {}
        for s in states:
            count = self.env["alpha.agency.licence"].search_count([("state", "=", s)])
            result[s.replace("_", " ").title()] = count
        return result

    def _get_upcoming_expiry(self):
        """Get records with upcoming expiry (within 30 days)."""
        today = fields.Date.today()
        expiry_threshold = fields.Date.to_string(
            fields.Date.from_string(today) + datetime.timedelta(days=30)
        )
        upcoming = {
            "licences": self.env["alpha.agency.licence"].search_count([
                ("expiry_date", ">=", today),
                ("expiry_date", "<=", expiry_threshold),
            ]),
            "devices": self.env["alpha.agency.device"].search_count([
                ("expiry_date", ">=", today),
                ("expiry_date", "<=", expiry_threshold),
            ]),
            "credentials": self.env["alpha.agency.credential"].search_count([
                ("expiry_date", ">=", today),
                ("expiry_date", "<=", expiry_threshold),
            ]),
        }
        return upcoming


class AgencyXLSXReport(models.AbstractModel):
    """XLSX Report for detailed agency data export."""
    _name = "report.alpha.agency_xlsx_report"
    _description = "Agency XLSX Report"
    _inherit = "report.report_xlsx.abstract"

    def _get_report_values(self, docids, data=None):
        """Generate XLSX report data."""
        agencies = self.env["alpha.agency"].browse(docids)
        report_data = []
        for agency in agencies:
            report_data.append({
                "agency_code": agency.code,
                "agency_name": agency.name,
                "agency_type": dict(agency._fields["agency_type"].selection).get(agency.agency_type, ""),
                "state": dict(agency._fields["state"].selection).get(agency.state, ""),
                "partner": agency.partner_id.name if agency.partner_id else "",
                "applications_count": len(agency.application_ids),
                "audits_count": agency.audit_count,
                "licences_count": len(agency.licence_ids),
                "devices_count": len(agency.device_ids),
            })
        return {
            "doc_ids": docids,
            "doc_model": "alpha.agency",
            "data": data,
            "report_data": report_data,
        }

    def create_xlsx_report(self, workbook, data):
        """Create XLSX workbook content."""
        report_data = data.get("report_data", [])
        sheet = workbook.add_worksheet("Agency Report")
        headers = [
            "Agency Code", "Agency Name", "Type", "State",
            "Partner", "Applications", "Audits", "Licences", "Devices"
        ]
        header_format = workbook.add_format({"bold": True, "bg_color": "#4472C4", "font_color": "white"})
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
        for row, record in enumerate(report_data, start=1):
            for col, key in enumerate(headers):
                value = record.get(key.lower().replace(" ", "_"))
                if value:
                    sheet.write(row, col, str(value))