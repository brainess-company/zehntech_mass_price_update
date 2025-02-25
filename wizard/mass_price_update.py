from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class MassPriceUpdate(models.TransientModel):
    """Change Price and Cost of Products by Percentage or Constant Value"""
    _name = 'mass.price.update'
    _description = "Mass Price Update"

    apply_to = fields.Selection(
        [('all', 'All Products'),
         ('category', 'Selected Categories'),
         ('attribute', 'Selected Attribute'),
         ('tag', 'Selected Tags'),
         ('selected', 'Selected Products')],
        default='selected', 
        string='Apply To', 
        required=True, 
        help='Specifies the scope of products to which the price or cost changes will apply'
    )

    apply_on = fields.Selection(
        [('price', 'Price'), ('cost', 'Cost')],
        default='price', 
        string='Apply On', 
        required=True,
        help='Specifies whether the changes will be applied to the sales price or the cost of the product'
    )

    change_type = fields.Selection(
        [('percentage', 'Percentage'), ('constant', 'Constant Value')],
        default='percentage', 
        string='Change Type', 
        required=True,
        help="Defines if the change will be a percentage increase/decrease or a constant value adjustment"
    )

    attribute_ids = fields.Many2many(
        'product.attribute', 
        string='Attributes', 
        help='Product attributes used to filter the products for the price or cost changes'
    )
    tag_ids = fields.Many2many(
        'product.tag', 
        string='Product Tags', 
        help='Tags assigned to products for selecting applicable items for changes'
    )

    change = fields.Float(
        string='Change (Constant)', 
        help='Constant value to be added or reduced from the product price or cost'
    )
    change_percentage = fields.Float(
        string='Change Percentage', 
        help='Percentage value to be applied for increasing or decreasing the product price or cost'
    )

    apply_type = fields.Selection(
        [('add', 'Add'), ('reduce', 'Reduce')],
        default='add', 
        string='Apply Type', 
        required=True,
        help='Determines whether the change will be an addition or reduction in the price or cost'
    )

    product_ids = fields.Many2many(
        'product.product', 
        string='Products', 
        domain="[('active', '=', True)]", 
        help='Specific products selected for price or cost changes'
    )
    category_ids = fields.Many2many(
        'product.category', 
        string='Categories', 
        help='Product categories used to filter applicable items for price or cost changes'
    )
    line_ids = fields.One2many(
        'change.price.line', 
        'mass_price_update_id', 
        readonly=True, 
        help='Lines showing the details of the price changes applied'
    )
    price_list_ids = fields.Many2many(
        'product.pricelist', 
        string='Price Lists', 
        help='Price lists affected by the mass price update'
    )

    min_price = fields.Float(
        string='Minimum Price', 
        help='The minimum price limit to be applied during the update, if specified'
    )
    max_price = fields.Float(
        string='Maximum Price', 
        help='The maximum price limit to be applied during the update, if specified'
    )
    round_price = fields.Boolean(
        string='Round Prices', 
        default=True, 
        help='Enable rounding for the updated prices to the nearest value as per rounding rules'
    )
    currency_id = fields.Many2one(
        'res.currency', 
        string="Target Currency", 
        required=True,
        default=lambda self: self.env.company.currency_id,
        help='The currency in which the price or cost changes are calculated and applied'
    )


    @api.onchange('apply_to')
    def _onchange_apply_to(self):
        """Update related fields based on 'apply_to' selection"""
        self._reset_fields()
        if self.apply_to == 'all':
            self.product_ids = self.env['product.product'].search([('active', '=', True)]).ids
        elif self.apply_to == 'category':
            self.product_ids = self.env['product.product'].search([('categ_id', 'in', self.category_ids.ids)]).ids
        elif self.apply_to == 'attribute':
            # Filter based on selected attributes
            if self.attribute_ids:
                domain = [('product_tmpl_id.attribute_line_ids.attribute_id', 'in', self.attribute_ids.ids)]
                self.product_ids = self.env['product.product'].search(domain).ids
        elif self.apply_to == 'tag':
            # Corrected domain to filter by product tags via product_tmpl_id.product_tag_ids
            if self.tag_ids:
                domain = [('product_tmpl_id.product_tag_ids', 'in', self.tag_ids.ids)]
                self.product_ids = self.env['product.product'].search(domain).ids
        elif self.apply_to == 'selected':
            self.product_ids = [(5,)]  # Clear products when selecting 'selected'

    def _reset_fields(self):
        """Reset product, category, and line fields"""
        self.product_ids = self.category_ids = self.line_ids = [(5,)]

    @api.onchange('product_ids', 'category_ids')
    def _onchange_products_categories(self):
        """Update lines based on selected products or categories"""
        try:
            products = self.env['product.product'].sudo().search(
                [('categ_id', 'in', self.category_ids.ids)] if self.category_ids else [('id', 'in', self.product_ids.ids)])
            self.write({'product_ids': products.ids, 'line_ids': [(5,)] + [(0, 0, {'product_id': p.id}) for p in products]})
        except Exception as e:
            raise UserError(_("Error updating products or categories: %s" % str(e)))
    @api.onchange('attribute_ids', 'tag_ids')
    def _onchange_attributes_tags(self):
        """Update products based on selected attributes or tags"""
        try:
            domain = []
            # Filter by attributes if any attributes are selected
            if self.attribute_ids:
                domain.append(('product_tmpl_id.attribute_line_ids.attribute_id', 'in', self.attribute_ids.ids))
            # Filter by tags if any tags are selected
            if self.tag_ids:
                domain.append(('product_tmpl_id.product_tag_ids', 'in', self.tag_ids.ids))
            # If no filters are applied, reset the product list
            if not domain:
                self.product_ids = [(5,)]  # Clear the product list if no attributes or tags are selected
            else:
                
                # Search for products based on the combined domain
                products = self.env['product.product'].search(domain)
                self.product_ids = products.ids  # Update the product_ids field with the filtered products
            # Clear the existing lines
            self.line_ids = [(5,)]
            # Create lines for each product after filtering
            for product in self.product_ids:
                self.line_ids = [(0, 0, {'product_id': product.id}) for product in products]

        except Exception as e:
            raise UserError(_("Error updating products or tags/attributes: %s" % str(e)))

    def _apply_price_or_cost_change(self, product, old_value, new_value):
        """Helper method to apply price or cost change"""
        try:
            if self.min_price:
                new_value = max(new_value, self.min_price)
            if self.max_price:
                new_value = min(new_value, self.max_price)
            if self.round_price:
                new_value = round(new_value)

            field_to_update = 'lst_price' if self.apply_on == 'price' else 'standard_price'
            setattr(product, field_to_update, new_value)

            return new_value
        except Exception as e:
            raise UserError(_("Error applying price or cost change: %s" % str(e)))

    def action_change_price(self):
        """Main function to change product prices or costs"""
        try:
            if not self.product_ids:
                raise UserError(_("Please select at least one product."))

            if self.change_type == 'percentage' and not self.change_percentage:
                raise UserError(_("Please enter the change percentage."))

            if self.change_type == 'constant' and not self.change:
                raise UserError(_("Please enter the constant change value."))

            # Calculate change factor based on the apply_type
            if self.change_type == 'percentage':
                change_factor = (1 + self.change_percentage) if self.apply_type == 'add' else (1 - self.change_percentage)
                change_value = None
            else:  # constant
                # Apply constant change based on apply_type
                if self.apply_type == 'add':
                    change_value = self.change  # Increase by constant value
                elif self.apply_type == 'reduce':
                    change_value = -self.change  # Decrease by constant value
                change_factor = None

            target_currency = self.currency_id

            if not target_currency:
                raise UserError(_("Please select a target currency."))

            log_model = self.env['mass.price.update.log']
            for product in self.product_ids:
                old_value = product.lst_price if self.apply_on == 'price' else product.product_tmpl_id.standard_price

                # Apply the change (percentage or constant)
                if self.change_type == 'percentage':
                    new_value = old_value * change_factor  # Apply percentage change
                else:  # constant
                    new_value = old_value + change_value  # Apply constant change

                new_value = self._apply_price_or_cost_change(product, old_value, new_value)

                # Log the change
                log_model.create({
                    'product_id': product.id,
                    'change_type': self.change_type,
                    'apply_type': self.apply_type,
                    'apply_on': self.apply_on,
                    'old_price': old_value if self.apply_on == 'price' else 0.0,
                    'new_price': new_value if self.apply_on == 'price' else 0.0,
                    'old_cost': old_value if self.apply_on == 'cost' else 0.0,
                    'new_cost': new_value if self.apply_on == 'cost' else 0.0,
                    'old_price_target_currency': old_value * target_currency.rate if self.apply_on == 'price' else 0.0,
                    'new_price_target_currency': new_value * target_currency.rate if self.apply_on == 'price' else 0.0,
                    'old_cost_target_currency': old_value * target_currency.rate if self.apply_on == 'cost' else 0.0,
                    'new_cost_target_currency': new_value * target_currency.rate if self.apply_on == 'cost' else 0.0,
                    'change_percentage': self.change_percentage * 100 if self.change_type == 'percentage' else 0.0,
                    'change_value': self.change if self.change_type == 'constant' else 0.0,
                    'min_price': self.min_price,
                    'max_price': self.max_price,
                    'round_price': self.round_price,
                    'currency_id': target_currency.id,
                })

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('The {} has been updated.').format(_('price') if self.apply_on == 'price' else _('cost')),
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        except Exception as e:
            raise UserError(_("Error changing price or cost: %s" % str(e)))
