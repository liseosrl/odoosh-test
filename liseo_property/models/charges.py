from odoo import models, fields, api, exceptions
from datetime import date
from odoo.exceptions import UserError, Warning

class PropCharges(models.Model):
    _name = 'prop.charges'
    _description = "Charges - Achats"
    _inherit = ['mail.thread']
    name = fields.Char(string='Description', required=True)
    description = fields.Html(String="Description")
    property_id = fields.Many2one('prop.properties', string="Chantier")
    supplier_id = fields.Many2one('res.partner', string="Fournisseur", domain="[('is_supplier', '=', True)]")
    attachment_ids = fields.Many2many('ir.attachment', 'attachment_charges_rel', 'charges_id', 'attach_id', string="Pièces jointes")
    cost = fields.Float(string='Montant')
    invoiced = fields.Boolean("Facturé")
    paid = fields.Boolean("Payé")