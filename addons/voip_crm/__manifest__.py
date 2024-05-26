# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "VoIP for CRM",
    "summary": "VoIP integration with CRM module.",
    "description": """Adds a button to schedule calls from leads in Kanban.""",
    "category": "Sales/CRM",
    "version": "1.0",
    "depends": ["base", "crm", "voip"],
    "auto_install": True,
    "data": ["views/crm_lead_views.xml"],
    "license": "OEEL-1",
}
