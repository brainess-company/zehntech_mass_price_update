from odoo import api, fields, models

class MassPriceUpdateLog(models.Model):
    """Log all price update activities from MassPriceUpdate and ChangePriceLine"""
    _name = 'mass.price.update.log'
    _description = "Mass Price Update Log"
    _order = 'update_date desc'

    update_date = fields.Datetime(
        string='Update Date',
        default=fields.Datetime.now,
        readonly=True,
        help="Date and time when the price update was logged"
    )
    user_id = fields.Many2one(
        'res.users',
        string='Updated By',
        default=lambda self: self.env.user,
        readonly=True,
        help="User who performed the update"
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        help="The product for which the price or cost was updated"
    )
    change_type = fields.Selection(
        [
            ('percentage', 'Percentage'),
            ('constant', 'Constant Value')
        ],
        string='Change Type',
        required=True,
        help="Type of change applied to the price or cost"
    )
    apply_type = fields.Selection(
        [
            ('add', 'Add'),
            ('reduce', 'Reduce')
        ],
        string='Apply Type',
        required=True,
        help="Specifies whether the value was added to or reduced from the original"
    )
    apply_on = fields.Selection(
        [
            ('price', 'Price'),
            ('cost', 'Cost')
        ],
        string='Apply On',
        required=True,
        help="Indicates whether the change was applied to the price or cost"
    )
    old_price = fields.Float(
        string='Old Price',
        digits='Product Price',
        help="Original price before the update"
    )
    new_price = fields.Float(
        string='New Price',
        digits='Product Price',
        help="Updated price after the change"
    )
    old_cost = fields.Float(
        string='Old Cost',
        digits='Product Price',
        help="Original cost before the update"
    )
    new_cost = fields.Float(
        string='New Cost',
        digits='Product Price',
        help="Updated cost after the change"
    )
    old_price_target_currency = fields.Float(
        string='Old Price in Target Currency',
        digits='Product Price',
        help="Original price in the target currency before the update"
    )
    new_price_target_currency = fields.Float(
        string='New Price in Target Currency',
        digits='Product Price',
        help="Updated price in the target currency after the change"
    )
    old_cost_target_currency = fields.Float(
        string='Old Cost in Target Currency',
        digits='Product Price',
        help="Original cost in the target currency before the update"
    )
    new_cost_target_currency = fields.Float(
        string='New Cost in Target Currency',
        digits='Product Price',
        help="Updated cost in the target currency after the change"
    )
    change_percentage = fields.Float(
        string='Change Percentage',
        help="Percentage of change applied to the price or cost",
        default=0.0
    )
    change_value = fields.Float(
        string='Change Value',
        help="Constant value of change applied to the price or cost",
        default=0.0
    )
    min_price = fields.Float(
        string='Minimum Price',
        help="Minimum price allowed for the product after the update"
    )
    max_price = fields.Float(
        string='Maximum Price',
        help="Maximum price allowed for the product after the update"
    )
    round_price = fields.Boolean(
        string='Rounded Price',
        default=False,
        help="Indicates whether the updated price was rounded"
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        help="Target currency used for price or cost conversion"
    )
