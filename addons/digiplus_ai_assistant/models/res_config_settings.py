from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ai_service_url = fields.Char(config_parameter="digiplus_ai_assistant.ai_service_url", default="http://ai-service:8000")
    ai_service_timeout = fields.Integer(config_parameter="digiplus_ai_assistant.ai_service_timeout", default=60)
    ai_model_name = fields.Char(config_parameter="digiplus_ai_assistant.ai_model_name", default="qwen2.5:0.5b")
    enable_auto_project_creation = fields.Boolean(config_parameter="digiplus_ai_assistant.enable_auto_project_creation", default=False)
    enable_human_validation = fields.Boolean(config_parameter="digiplus_ai_assistant.enable_human_validation", default=True)
