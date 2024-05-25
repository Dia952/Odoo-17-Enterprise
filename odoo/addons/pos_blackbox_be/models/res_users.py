from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class ResUser(models.Model):
    _inherit = "res.users"

    # bis number is for foreigners in Belgium
    insz_or_bis_number = fields.Char(
        "INSZ or BIS number", help="Social security identification number"
    )
    session_clocked_ids = fields.Many2many(
        "pos.session",
        "users_session_clocking_info",
        string="Session Clocked In",
        help="This is a technical field used for tracking the status of the session for each users.",
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["insz_or_bis_number"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["insz_or_bis_number"]

    @api.constrains("insz_or_bis_number")
    def _check_insz_or_bis_number(self):
        for rec in self:
            if rec.insz_or_bis_number and not self.is_valid_insz_or_bis_number(rec.insz_or_bis_number):
                raise ValidationError(_("The INSZ or BIS number is not valid."))

    def is_valid_insz_or_bis_number(self, number):
        if not number:
            return False
        if len(number) != 11 or not number.isdigit():
            return False

        partial_number = number[:-2]
        modulo = int(partial_number) % 97

        return modulo == 97 - int(number[-2:])

    @api.model_create_multi
    def create(self, values):
        for value_dict in values:
            filtered_values = {
                field: ("********" if field in self._get_invalidation_fields() else value)
                for field, value in value_dict.items()
            }

            self.env["pos_blackbox_be.log"].sudo().create(
                filtered_values, "create", self._name, value_dict.get("name")
            )

        return super(ResUser, self).create(values)

    def write(self, values):
        filtered_values = {
            field: ("********" if field in self._get_invalidation_fields() else value)
            for field, value in values.items()
        }
        for user in self:
            self.env["pos_blackbox_be.log"].sudo().create(
                filtered_values, "modify", user._name, user.name
            )

        return super(ResUser, self).write(values)

    def unlink(self):
        for user in self:
            self.env["pos_blackbox_be.log"].sudo().create(
                {}, "delete", user._name, user.name
            )

        return super(ResUser, self).unlink()
