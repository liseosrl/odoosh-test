from odoo import models, fields, api, exceptions
from datetime import date
from odoo.exceptions import UserError, Warning
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError

class PropProperties(models.Model):
    _name = 'prop.properties'
    _rec_name = 'friendly_name'
    friendly_name = fields.Char('Nom', compute='_compute_friendly_name')

    @api.depends('street', 'city')
    def _compute_friendly_name(self):
        for rec in self:
            if rec.name and rec.street and rec.city:
                rec.friendly_name = rec.name + " - " + rec.street + " à " + rec.city

    _description = "Biens"
    _inherit = ['mail.thread']
    name = fields.Char(string='Référence du chantier', readonly=True, required=True, copy=False, default='New')
    sequence = fields.Char(string='Nom de la séquence')
    active = fields.Boolean(string='Active', default=True)
    color = fields.Integer(string='Couleur')
    stage = fields.Selection([
        ('0_nouveau', 'Nouveau'),
        ('1_etude', 'Etude'),
        ('2_permis', 'Permis'),
        ('3_grosoeuvre', 'Gros oevre'),
        ('4_finitions', 'Finitions'),
        ('5_termine', 'Terminé'),
        ('6_loc', 'Loué'),
        ('7_vendu', 'Vendu'),
    ], string="Etape", default='0_nouveau')

    street = fields.Char(string='Rue')
    cp = fields.Char(string='Code postal')
    city = fields.Char(string='Localité')
    country_id = fields.Many2one('res.country', string='Pays', ondelete='restrict')
    type = fields.Selection([
        ('0_immeuble', 'Immeuble à appartements'),
        ('1_appartement', 'Appartement'),
        ('2_maison', 'Maison'),
        ('3_terrain', 'Terrain'),
        ('4_bureau', 'Bureau'),
        ('5_commerce', 'Commerce'),
        ('6_garage', 'Garage'),
        ('7_autre', 'Autre'),
    ], string="Type", default='0_immeuble')
    initial_budget = fields.Float(string='Budget initial')
    real_cost = fields.Float(string='Montant facturé', compute="_compute_jobs_amount")
    initial_cost = fields.Float(string='Montant des devis', compute="_compute_jobs_amount")
    margin = fields.Float(string='Différence', compute="_compute_jobs_amount")
    owner_id = fields.Many2one('res.partner', string="Propriétaire")
    surface = fields.Float(string="Surface (m²)")
    capacity = fields.Integer(string="Capacité (personnes)")
    parent_id = fields.Many2one('prop.properties', string="Immeuble lié", domain="[('type', '=', '0_immeuble')]")
    jobs_ids = fields.One2many(comodel_name='prop.jobs', inverse_name='property_id', string='Poste')
    credit = fields.Boolean(string="Crédit")
    bank_id = fields.Many2one('res.partner', string="Banque", domain="[('is_bank', '=', True)]")
    credit_movement_ids = fields.One2many(comodel_name='prop.credit', inverse_name='property_id', string='Libérations')
    credit_amount = fields.Float(string="Montant du crédit")
    credit_amount_used = fields.Float(string="Montant utilisé", compute="_compute_credit_amount")
    credit_amount_remain = fields.Float(string="Montant restant", compute="_compute_credit_amount")
    credit_mens = fields.Float(string="Mensualité")

    occupant_id = fields.Many2one('res.partner', string="Locataire")
    rent_price = fields.Float(string='Loyer')
    is_rented = fields.Boolean(string="Est loué")
    rental_start = fields.Date(string="Début du bail")
    rental_end = fields.Date(string="Fin du bail")
    rental_invoice_ids = fields.One2many(comodel_name='account.move', inverse_name='property_id', string="Loyers")
    last_rental_invoice = fields.Char('Dernier mois facturé')
    rental_total_amount = fields.Float('Loyers perçus', compute='_compute_rental_total_amount')
    charges_total_amount = fields.Float('Dépenses', compute='_compute_charges_total_amount')
    property_revenue = fields.Float('Rentabilité', compute='_compute_property_revenue')
    expected_profitability_date = fields.Char(string="Date prévue d'amortissement", compute='_compute_profitability_date')

    analytic_account_id = fields.Many2one('account.analytic.account', string="Compte analytique")
    charges_ids = fields.One2many(comodel_name='prop.charges', inverse_name="property_id", string="Dépenses")

    other_move_ids = fields.One2many(comodel_name='account.move', inverse_name="other_property_id", string="Factures")
    other_move_amount = fields.Float('Montant', compute='_compute_other_move_amount')

    @api.depends('other_move_ids')
    def _compute_other_move_amount(self):
        for property in self:
            out_invoices = sum(property.other_move_ids.filtered(lambda m: m.move_type == 'out_invoice').mapped('amount_untaxed_signed'))
            in_invoices = sum(property.other_move_ids.filtered(lambda m: m.move_type == 'in_invoice').mapped('amount_untaxed_signed'))
            property.other_move_amount = in_invoices - out_invoices

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('seq_properties') or 'New'
        if not vals.get('account.analytic.account'):
            self.env['account.analytic.account'].create({
                'name': vals['name'],
            })
        result = super(PropProperties, self).create(vals)
        return result


    @api.depends('rental_invoice_ids')
    def _compute_rental_total_amount(self):
        for rec in self:
            total = 0
            for line in rec.rental_invoice_ids:
                total += line.amount_total_signed
            rec.rental_total_amount = total

    @api.depends('charges_total_amount')
    def _compute_charges_total_amount(self):
        for rec in self:
            total = 0
            for line in rec.charges_ids:
                total += line.cost
            rec.charges_total_amount = total

    @api.depends('rental_total_amount', 'charges_total_amount', 'real_cost', 'other_move_amount')
    def _compute_property_revenue(self):
        for rec in self:
            total = 0
            total += rec.rental_total_amount
            total -= rec.charges_total_amount
            total -= rec.real_cost
            total -= rec.other_move_amount
            rec.property_revenue = total

    @api.depends('rental_total_amount', 'charges_total_amount', 'real_cost')
    def _compute_profitability_date(self):
        for rec in self:
            if rec.charges_total_amount or rec.real_cost and rec.rent_price:
                amount_paid = rec.charges_total_amount + rec.real_cost - rec.rental_total_amount
                try :
                    months = round(amount_paid / rec.rent_price)
                    if months > 0:
                        rec.expected_profitability_date = str(months) + " mois"
                    else :
                        rec.expected_profitability_date = "Déja amorti"
                except ZeroDivisionError:
                    rec.expected_profitability_date = "N.C."
            else:
                rec.expected_profitability_date = "N.C."



    @api.onchange('parent_id')
    def _compute_address(self):
        for rec in self:
            if rec.parent_id:
                rec['street'] = rec.parent_id.street
                rec['cp'] = rec.parent_id.cp
                rec['city'] = rec.parent_id.city
                rec['country_id'] = rec.parent_id.country_id

    @api.onchange('credit_movement_ids')
    def _compute_credit_amount(self):
        for rec in self:
            amount_used = 0
            amount_remain = rec.credit_amount
            for line in self.credit_movement_ids:
                if line.is_paid == True:
                    amount_used += line.amount
                    amount_remain -= line.amount
            rec['credit_amount_used'] = amount_used
            rec['credit_amount_remain'] = amount_remain

    @api.onchange('jobs_ids')
    def _compute_jobs_amount(self):
        for rec in self:
            real_cost = 0
            initial_cost = 0
            for line in rec.jobs_ids:
                real_cost += line.real_cost
                initial_cost += line.initial_budget
            rec['real_cost'] = real_cost
            rec['initial_cost'] = initial_cost
            rec['margin'] = initial_cost - real_cost

    def get_default_jobs(self):
        job_lines = self.env['prop.templates'].search([])
        for line in job_lines:
            self.env['prop.jobs'].create({
                'stage': '0_nouveau',
                'template_id': line.id,
                'property_id': self.id,
            })


    def create_past_rental_invoices(self):

        if not self.rental_start or self.rent_price < 1 or not self.occupant_id:
            raise ValidationError("Veuillez compléter les dates de bail, le montant du loyer et le nom du locataire.")

        journal_id = self.env['account.journal'].search([('name', '=', 'Loyers')], limit=1).id
        delta = (date.today().year - self.rental_start.year) * 12 + (date.today().month - self.rental_start.month)
        product_id = self.sudo().env['product.product'].search([('default_code', '=', 'LOYER')], limit=1).id

        loyer_date = self.rental_start

        while loyer_date < date.today() and loyer_date < self.rental_end:
            account_move = self.env['account.move'].with_context(default_move_type='out_invoice').create({
                'move_type': 'out_invoice',
                'invoice_date': loyer_date,
                'journal_id': journal_id,
                'property_id': self.id,
                'partner_id': self.occupant_id.id,
            })
            invoice_line_vals = []

            invoice_line_val = {
                'product_id': product_id,
                'quantity': 1,
                'price_unit': self.rent_price,

            }
            invoice_line_vals.append((0, 0, invoice_line_val))
            account_move.invoice_line_ids = invoice_line_vals
            account_move.action_post()
            loyer_date = loyer_date + relativedelta(months=+1)
        self.last_rental_invoice = loyer_date.strftime("%Y-%m")

    def generate_invoices(self):
        biens = self.env['prop.properties'].search([('is_rented', '!=', False), ('rental_start', '!=', False), ('rent_price', '!=', False), ('rental_end', '>', date.today()), ('occupant_id', '!=', False)])
        product_id = self.sudo().env['product.product'].search([('default_code', '=', 'LOYER')], limit=1).id
        for bien in biens:
            if bien.last_rental_invoice != date.today().strftime("%Y-%m"):
                bien.last_rental_invoice = date.today().strftime("%Y-%m")
                journal_id = self.env['account.journal'].search([('name', '=', 'Loyers')], limit=1).id
                account_move = self.env['account.move'].with_context(default_move_type='out_invoice').create({
                    'move_type': 'out_invoice',
                    'invoice_date': date.today(),
                    'journal_id': journal_id,
                    'property_id': bien.id,
                    'partner_id': bien.occupant_id.id,
                })
                invoice_line_vals = []

                invoice_line_val = {
                    'product_id': product_id,
                    'name': 'Loyer - ' + str(bien.last_rental_invoice),
                    'quantity': 1,
                    'price_unit': bien.rent_price,

                }
                invoice_line_vals.append((0, 0, invoice_line_val))
                account_move.invoice_line_ids = invoice_line_vals
                account_move.action_post()










