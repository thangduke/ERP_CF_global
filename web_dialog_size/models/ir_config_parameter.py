from odoo.models import Model, api
from ast import literal_eval

class IrConfigParameter(Model):
    _inherit = "ir.config_parameter"

    @api.model
    def get_web_dialog_size_config(self):
        get_param = self.sudo().get_param
        try:
            default_maximize = literal_eval(get_param("web_dialog_size.default_maximize", "False"))
        except (ValueError, SyntaxError):
            default_maximize = False
            
        return {
            "default_maximize": default_maximize
        }