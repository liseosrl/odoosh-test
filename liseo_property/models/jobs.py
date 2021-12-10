from odoo import models, fields, api, exceptions
from datetime import date
from odoo.exceptions import UserError, Warning

class PropJobs(models.Model):
    _name = 'prop.jobs'
    _description = "Biens"
    _inherit = ['mail.thread']
    name = fields.Char(string='Référence du poste', readonly=True, required=True, copy=False, default='New')
    property_id = fields.Many2one('prop.properties', string="Chantier")
    supplier_id = fields.Many2one('res.partner', string="Fournisseur", domain="[('is_supplier', '=', True)]")
    template_id = fields.Many2one('prop.templates', string="Poste")
    stage = fields.Selection([
        ('0_nouveau', 'Nouveau'),
        ('1_devis', 'Devis'),
        ('2_encours', 'En cours'),
        ('3_termine', 'Terminé'),
    ], string="Etape", default='0_nouveau')
    attachment_ids = fields.Many2many('ir.attachment', 'attachment_rel', 'job_id', 'attach_id', string="Pièces jointes")
    initial_budget = fields.Float(string='Montant des devis')
    real_cost = fields.Float(string='Montant facturé', compute="_compute_real_cost")
    invoice_ids = fields.One2many(comodel_name='account.move', inverse_name='property_job_id', string='Factures'
                                  , domain="[('move_type', '=', 'in_invoice')]")
    invoiced = fields.Boolean("Facturé", compute="_compute_invoice_status")
    paid = fields.Boolean("Payé", compute="_compute_invoice_status")

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('seq_jobs') or 'New'
        result = super(PropJobs, self).create(vals)
        return result

    @api.onchange('invoice_ids')
    def _compute_invoice_status(self):
        for rec in self:
            count = 0
            unpaid = 0
            for line in rec.invoice_ids:
                count += 1
                if line.payment_state != 'paid':
                    unpaid += 1
            if count >= 1:
                rec['invoiced'] = True
            else:
                rec['invoiced'] = False
            if unpaid == 0 and count >= 1:
                rec['paid'] = True
            else:
                rec['paid'] = False

    @api.onchange('invoice_ids')
    def _compute_real_cost(self):
        for rec in self:
            real_cost = 0
            for line in rec.invoice_ids:
                real_cost += line.amount_untaxed
            rec['real_cost'] = real_cost




