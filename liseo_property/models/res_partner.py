from odoo import models, fields, api, exceptions
from datetime import date
from odoo.exceptions import UserError, Warning

class resPartnerOverrides(models.Model):
    _inherit = "res.partner"
    is_bank = fields.Boolean(string="Banque")
    is_supplier = fields.Boolean(string="Fournisseur")