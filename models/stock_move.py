# -*- coding: utf-8 -*-


from odoo import models, fields, api
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = "stock.move"

    # MODEL FIELDS
    request_line_id = fields.Many2one("stock.request.line", required=False,
                                      states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
