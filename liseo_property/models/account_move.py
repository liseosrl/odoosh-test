
from odoo import models, fields, api, exceptions
from datetime import date
from odoo.exceptions import UserError, Warning

class accountMoveOverrides(models.Model):
    _inherit = "account.move"
    property_job_id = fields.Many2one('prop.jobs', string="Chantier")
    property_id = fields.Many2one('prop.properties', string="Bien")
    attachment_ids = fields.Many2many('ir.attachment', 'attachment_move_rel', 'move_id', 'attach_id', string="Pièces jointes")
    other_property_id = fields.Many2one('prop.properties', string="Bien lié")
