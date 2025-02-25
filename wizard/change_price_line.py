from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class ChangePriceLine(models.TransientModel):
    """One2many for aligning the products with new price"""
    _name = 'change.price.line'
    _rec_name = 'product_id'
    _description = "Change Price Line"

    mass_price_update_id = fields.Many2one(
        'mass.price.update', 
        string='Number', 
        help='Reference to the mass price update entry associated with this line'
    )
    product_id = fields.Many2one(
        'product.product', 
        string='Product', 
        required=True, 
        domain="[('active', '=', True)]", 
        help='The product selected for price or cost changes'
    )
    current_price = fields.Float(
        string='Current Price', 
        digits='Product Price', 
        related='product_id.lst_price', 
        help='The current sales price of the product'
    )
    new_price = fields.Float(
        string='New Price', 
        digits='Product Price', 
        compute='_compute_new_values', 
        help='The newly computed sales price after applying changes'
    )
    current_cost = fields.Float(
        string='Current Cost', 
        digits='Product Price', 
        related='product_id.standard_price', 
        help='The current cost of the product before changes'
    )
    new_cost = fields.Float(
        string='New Cost', 
        digits='Product Price', 
        compute='_compute_new_values', 
        help='The newly computed cost after applying changes'
    )
    currency_id = fields.Many2one(
        'res.currency', 
        string='Currency', 
        related='product_id.currency_id', 
        help='The currency in which the product prices and costs are expressed'
    )
    old_price_target_currency = fields.Float(
        string='Old Price in Target Currency', 
        digits='Product Price', 
        help='The previous sales price of the product converted to the target currency'
    )
    new_price_target_currency = fields.Float(
        string='New Price in Target Currency', 
        digits='Product Price', 
        help='The updated sales price of the product converted to the target currency'
    )
    old_cost_target_currency = fields.Float(
        string='Old Cost in Target Currency', 
        digits='Product Price', 
        help='The previous cost of the product converted to the target currency'
    )
    new_cost_target_currency = fields.Float(
        string='New Cost in Target Currency', 
        digits='Product Price', 
        help='The updated cost of the product converted to the target currency'
    )

    @api.depends('mass_price_update_id.apply_on',
                 'mass_price_update_id.change', 'mass_price_update_id.change_percentage',
                 'mass_price_update_id.apply_type', 'mass_price_update_id.change_type',
                 'mass_price_update_id.currency_id')
    def _compute_new_values(self):
        """Compute new price and cost based on change type and target currency"""
        try:
            for record in self:
                update = record.mass_price_update_id
                if not update:
                    continue

                current_value = record.current_price if update.apply_on == 'price' else record.current_cost
                target_currency_rate = update.currency_id.rate if update.currency_id else 1

                # Determine the adjustment factor or constant value
                if update.change_type == 'percentage':
                    factor = 1 + (update.change_percentage ) if update.apply_type == 'add' else 1 - (update.change_percentage)
                    adjusted_value = current_value * factor
                else:  # Constant change
                    constant = update.change if update.apply_type == 'add' else -update.change
                    adjusted_value = current_value + constant

                # Assign new price or cost based on apply_on
                if update.apply_on == 'price':
                    record.new_price = adjusted_value
                    record.new_cost = False
                else:
                    record.new_cost = adjusted_value
                    record.new_price = False

                # Convert to target currency if applicable
                record.old_price_target_currency = record.current_price * target_currency_rate
                record.new_price_target_currency = record.new_price * target_currency_rate if record.new_price else 0.0
                record.old_cost_target_currency = record.current_cost * target_currency_rate
                record.new_cost_target_currency = record.new_cost * target_currency_rate if record.new_cost else 0.0
        except Exception as e:
            raise UserError(_("Error calculating new values: %s" % str(e)))
