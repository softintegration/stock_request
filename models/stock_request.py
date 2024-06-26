# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError,ValidationError
from odoo.tools.float_utils import float_compare


class StockRequest(models.Model):
    _name = "stock.request"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'cancel.motif.class']
    _description = "Stock request"
    _order = "date asc, id desc"

    @api.model
    def _default_scheduled_date(self):
        return fields.Datetime.now()

    @api.model
    def _get_default_location_domain(self):
        return [('usage', '=', 'internal')]

    date = fields.Datetime(
        'Creation Date',
        default=fields.Datetime.now, index=True, track_visibility='onchange',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help="Creation Date, usually the time of the order")
    date_done = fields.Datetime('Validation date', copy=False, readonly=True, help="Completion Date of Transfer")
    request_user_id = fields.Many2one('res.users', string='Requested By', index=True,
                                      states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
                                      default=lambda self: self.env.user)

    name = fields.Char(
        'Reference', copy=False, index=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    location_id = fields.Many2one(
        'stock.location', "Source Location",
        readonly=True, required=True,
        states={'draft': [('readonly', False)]},
        domain=lambda self: self._get_default_location_domain())
    location_dest_id = fields.Many2one(
        'stock.location', "Destination Location",
        readonly=True, required=True,
        states={'draft': [('readonly', False)]},
        domain=lambda self: self._get_default_location_domain())

    scheduled_date = fields.Datetime(
        'Scheduled Date', default=_default_scheduled_date,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})

    move_type = fields.Selection([
        ('direct', 'As soon as possible'), ('one', 'When all products are ready')], 'Shipping Policy',
        default='direct', required=False,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help="It specifies goods to be deliver partially or all at once")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Cancel')
    ], string='State', default='draft')

    has_scrap_move = fields.Boolean(
        'Has Scrap Moves', compute='_has_scrap_move')
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type',
        required=False,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})

    company_id = fields.Many2one(
        'res.company', 'Company', default=lambda s: s.env.company.id,
        index=True, required=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, )

    move_line_ids = fields.One2many('stock.request.line', 'request_id',
                                    states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    note = fields.Text('Notes')
    pickings_count = fields.Integer(compute='_compute_pickings_count')

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Reference must be unique per company!'),
    ]

    """@api.constrains('location_id','location_dest_id')
    def _check_locations(self):
        for each in self:
            if each.location_id and each.location_dest_id and each.location_id.id == each.location_dest_id.id:
                raise UserError(_("Source and destination location can not be the same!"))
            location_warehouse = each.location_id.get_warehouse()
            location_dest_warehouse = each.location_dest_id.get_warehouse()
            if location_warehouse.id != location_dest_warehouse.id:
                raise UserError(_("Location and destination location warehouses must be the same"))"""

    def _compute_pickings_count(self):
        for each in self:
            each.pickings_count = each._get_pickings(count=True)

    def action_view_pickings(self):
        self.ensure_one()
        domain = [('id', 'in', self._get_pickings().ids)]
        return {
            'name': _('Stock pickings'),
            'view_mode': 'tree,form',
            'views': [(self.env.ref('stock.vpicktree').id, 'tree'),
                      (self.env.ref('stock.view_picking_form').id, 'form')],
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': domain,
        }

    def _get_pickings(self, count=False):
        self.ensure_one()
        domain = [('request_id', '=', self.id)]
        if count:
            return self.env['stock.picking'].search_count(domain)
        return self.env['stock.picking'].search(domain)

    def _check_action_done(self):
        for each in self:
            if not each.move_line_ids:
                raise ValidationError(_("Stock request lines are required in order to validate"))
            if any(float_compare(line.product_uom_qty, 0.0, precision_rounding=line.product_id.uom_id.rounding) <= 0 for
                   line in each.move_line_ids):
                raise ValidationError(_("All requested Qty(s) must be positive!"))
            if not each.picking_type_id:
                raise ValidationError(_("Operation Type is required before validation"))

    def action_done(self):
        self._check_action_done()
        for each in self:
            name = self.env.ref('stock_request.sequence_stock_request').next_by_id()
            each.write({'name': name})
        self._action_done()
        self.move_line_ids.action_done()
        self._create_picking()

    def _action_done(self):
        self.write({'state': 'done'})

    def _check_action_cancel(self):
        for each in self:
            if len(each._get_pickings().filtered(lambda p: p.state not in ('draft', 'cancel'))) > 0:
                raise UserError(_("You have to cancel related pickings before cancel the stock request %s") % each.name)

    def action_cancel(self):
        self._check_action_cancel()
        self._action_cancel()

    def _action_cancel(self):
        self.write({'state': 'cancel'})

    def unlink(self):
        self.action_cancel()
        return super(StockRequest, self).unlink()

    # @api.multi
    # def _check_request_state(self,state):
    #    for each in self:
    #        if state == 'validate':
    #            if not each.move_line_ids:
    #                raise UserError(_("Stock request lines are required in order to validate"))
    #            if any(float_compare(line.product_uom_qty, 0.0, precision_rounding=line.product_id.uom_id.rounding) <= 0 for line in each.move_line_ids):
    #                raise UserError(_("All requested Qty(s) must be positive!"))
    # elif state == 'cancel':
    # pickings = each._get_pickings()
    # my_internals = self.env['stock.move'].search([('request_line_id','in',each.move_line_ids.ids),
    #                                              ('picking_id','not in',internals.ids)]).mapped("picking_id")
    # for move in my_internals:
    #    if inter.state != 'cancel':
    #        raise UserError("Veuillez annuler le transfert <%s>"%inter.name)
    # for int_to_cancel in internals:
    #    int_to_cancel.action_cancel()

    def _create_picking(self):
        pickings = self.env['stock.picking']
        for each in self:
            pickings |= self.env['stock.picking'].create(each._prepare_picking())
        pickings.action_confirm()

    def _get_picking_type(self):
        self.ensure_one()
        return self.location_id.warehouse_id.int_type_id

    def _prepare_picking(self):
        self.ensure_one()
        picking_dict = {
            'request_id': self.id,
            'origin': self.name,
            'move_type': 'direct',
            'state': 'draft',
            'scheduled_date': self.scheduled_date,
            'date': self.date,
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id,
            'picking_type_id': self.picking_type_id and self.picking_type_id.id or self._get_picking_type().id,
            'company_id': self.location_id.company_id.id,
            'move_lines': [(0, 0, move_line._prepare_move_line(self.location_id.id, self.location_dest_id.id,
                                                               company=self.location_id.company_id.id)) for move_line in
                           self.move_line_ids]
        }
        return picking_dict


class StockRequestLine(models.Model):
    _name = "stock.request.line"

    request_id = fields.Many2one(
        'stock.request', 'Request', ondelete='cascade')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Cancel')
    ], string='Status', default='draft')
    product_id = fields.Many2one('product.product', 'Product', ondelete="cascade", check_company=True,
                                 domain="[('type', '!=', 'service'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
                                 index=True, required=True)
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure', required=True,
                                     states={'draft': [('readonly', False)]}, readonly=True)
    product_uom_qty = fields.Float('Requested Qty', default=0.0, digits='Product Unit of Measure',
                                   required=True, states={'draft': [('readonly', False)]}, readonly=True)
    received_qty = fields.Float('Received Qty', default=0.0, digits='Product Unit of Measure',
                                compute='_compute_received_qty', store=False)
    location_id = fields.Many2one('stock.location', 'From', required=False, states={'draft': [('readonly', False)]},
                                  readonly=True, related='request_id.location_id', store=True)
    location_dest_id = fields.Many2one('stock.location', 'To', required=False, states={'draft': [('readonly', False)]},
                                       readonly=True, related='request_id.location_dest_id', store=True)
    company_id = fields.Many2one(related='request_id.company_id')
    date_expected = fields.Datetime('Expected Date', default=lambda self: fields.Datetime.now(), index=True,
                                    required=True,
                                    states={'draft': [('readonly', False)]}, readonly=True,
                                    help="Scheduled date for the processing of this line")

    @api.onchange('product_id', 'product_uom_id')
    def _onchange_product_id(self):
        if self.product_id:
            if not self.product_uom_id or self.product_uom_id.category_id != self.product_id.uom_id.category_id:
                self.product_uom_id = self.product_id.uom_id.id

    def _prepare_move_line(self, location_id, location_dest_id, company=False):
        self.ensure_one()
        return {
            'name': self.product_id.name,
            'date': self.request_id.date,
            'company_id': company or self.env.company.id,
            # 'date_expected': self.date_expected,
            'product_id': self.product_id.id,
            'product_uom_qty': self.product_uom_qty,
            'product_uom': self.product_uom_id.id,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'request_line_id': self.id,
        }

    @api.depends('request_id.pickings_count')
    def _compute_received_qty(self):
        for each in self:
            related_moves = each.request_id._get_pickings().mapped("move_lines") \
                .filtered(lambda mv: mv.state == 'done'
                                     and mv.product_id.id == each.product_id.id
                                     and mv.product_uom.id == each.product_uom_id.id
                                     and mv.location_id.id == each.location_id.id
                                     and mv.location_dest_id.id == each.location_dest_id.id)
            # we have to take in account the returns
            returned_moves = related_moves.mapped("move_dest_ids").filtered(lambda mv: mv.state == 'done')
            each.received_qty = sum(move.product_uom_qty for move in related_moves) - sum(
                move.product_uom_qty for move in returned_moves)

    def action_done(self):
        self._action_done()

    def _action_done(self):
        self.write({'state': 'done'})
