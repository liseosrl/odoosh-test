from odoo import models, fields, api, exceptions
from datetime import date
from odoo.exceptions import UserError, Warning

class PropCredit(models.Model):
    _name = 'prop.credit'
    _description = "Libérations de crédit"
    _inherit = ['mail.thread']
    name = fields.Char(string='Référence', readonly=True, required=True, copy=False, default='New')
    property_id = fields.Many2one('prop.properties', string="Chantier")
    template_id = fields.Many2one('prop.templates', string="Poste")
    description = fields.Char(string="Motif")
    date_dem = fields.Date('Date de demande')
    date_lib = fields.Date('Date de libération', compute="_compute_date_lib")
    is_paid = fields.Boolean("Libéré")
    amount = fields.Float(string="Montant")



    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('seq_credit') or 'New'
        result = super(PropCredit, self).create(vals)
        return result

    @api.onchange('is_paid')
    def _compute_date_lib(self):
        for rec in self:
            if rec.is_paid:
                if not rec.date_dem:
                    rec['date_dem'] = date.today()
                if not rec.date_lib:
                    rec['date_lib'] = date.today()
            else:
                rec['date_dem'] = rec.date_dem
                rec['date_lib'] = rec.date_lib