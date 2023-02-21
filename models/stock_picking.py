# -*- coding: utf-8 -*- 


from odoo import models, fields, api
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    request_id = fields.Many2one("stock.request", string='Stock request source', required=False,
                                 states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},copy=True)
    request_user_id = fields.Many2one('res.users', related='request_id.create_uid', string='Request user')
