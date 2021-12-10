from odoo import models, fields, api, exceptions
from datetime import date
from odoo.exceptions import UserError, Warning

class PropTemplates(models.Model):
    _name = 'prop.templates'
    _description = "Postes"
    name = fields.Char(string="Poste")
    sequence = fields.Integer(string="Séquence")