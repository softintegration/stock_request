# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.model
    def _get_transit_location_id_domain(self):
        return [('usage','=','internal')]

    module_stock_request_by_transit = fields.Boolean("Stock request by transit",
        help="Possibility to make transfers that go through transit locations.")
    transit_location_id = fields.Many2one('stock.location',domain=lambda self:self._get_transit_location_id_domain())


    def set_values(self):
        super(ResConfigSettings, self).set_values()
        IrDefault = self.env['ir.default'].sudo()
        IrDefault.set('res.config.settings', "transit_location_id",
                      self.transit_location_id and self.transit_location_id.id or False,
                      company_id=self.company_id.id or self.env.user.company_id.id)
