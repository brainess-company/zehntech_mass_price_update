import io
import base64
import xlsxwriter
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_date

class PriceChangeReport(models.Model):
    _name = 'price.change.report'
    _description = 'Price Change Report'
    _rec_name = 'highest_increase_product_id'
    
    start_date = fields.Date(
        string="Start Date", 
        required=True, 
        help="The starting date for the price change report period"
    )
    end_date = fields.Date(
        string="End Date", 
        required=True, 
        help="The ending date for the price change report period"
    )
    currency_id = fields.Many2one(
        'res.currency', 
        string="Currency", 
        required=True, 
        default=lambda self: self.env.company.currency_id, 
        help="The currency in which the report values will be calculated"
    )
    total_changes = fields.Integer(
        string="Total Changes", 
        readonly=True, 
        help="The total number of price changes within the selected period"
    )
    highest_increase_product_id = fields.Many2one(
        'product.product', 
        string="Highest Increase Sale", 
        readonly=True, 
        help="The product with the highest price increase during the report period"
    )
    highest_decrease_product_id = fields.Many2one(
        'product.product', 
        string="Highest Decrease Sale", 
        readonly=True, 
        help="The product with the highest price decrease during the report period"
    )
    revenue_before = fields.Float(
        string="Revenue Before", 
        readonly=True, 
        help="The total revenue before the price changes during the selected period"
    )
    revenue_after = fields.Float(
        string="Revenue After", 
        readonly=True, 
        help="The total revenue after the price changes during the selected period"
    )
    revenue_before_converted = fields.Float(
        string="Revenue Before (In chosen currency)", 
        readonly=True, 
        help="The total revenue before the price changes, converted to the chosen currency"
    )
    revenue_after_converted = fields.Float(
        string="Revenue After (In chosen currency)", 
        readonly=True, 
        help="The total revenue after the price changes, converted to the chosen currency"
    )
    profitability = fields.Float(
        string="Profitability Change (%)", 
        help="The percentage change in profitability resulting from the price changes"
    )
    product_ids = fields.Many2many(
        'product.product', 
        string="Products", 
        help="The list of products included in this price change report"
    )
    export_name = fields.Char(
        default="Price_Change_Report.xlsx", 
        string="Export File Name", 
        help="The default file name used when exporting the report"
    )


    @api.onchange('start_date', 'end_date', 'currency_id')
    def _onchange_dates(self):
        """Trigger report generation when dates or currency are set."""
        try:
            if self.start_date and self.end_date:
                if self.start_date > self.end_date:
                    raise UserError(_("Start Date cannot be later than End Date."))
                self.generate_report()
        except Exception as e:
            raise UserError(_("Error during date validation or report generation: %s") % e)

    def generate_report(self):
        try:
            logs = self.env['mass.price.update.log'].search([
                ('update_date', '>=', self.start_date),
                ('update_date', '<=', self.end_date)
            ])

            if not logs:
                raise UserError(_("No price change logs found in the given date range."))

            product_sales_before, product_sales_after = {}, {}

            for log in logs:
                product = log.product_id
                sales_before = self._get_sales_for_period(product, '<', log.update_date)
                sales_after = self._get_sales_for_period(product, '>=', log.update_date)

                product_sales_before[product.id] = sum(line.product_uom_qty * line.price_unit for line in sales_before)
                product_sales_after[product.id] = sum(line.product_uom_qty * line.price_unit for line in sales_after)

            highest_increase_product = max(
                product_sales_after, 
                key=lambda pid: product_sales_after[pid] - product_sales_before.get(pid, 0), 
                default=None
            )
            highest_decrease_product = min(
                product_sales_after, 
                key=lambda pid: product_sales_after[pid] - product_sales_before.get(pid, 0), 
                default=None
            )

            revenue_before = sum(product_sales_before.values())
            revenue_after = sum(product_sales_after.values())
            profitability = ((revenue_after - revenue_before) / revenue_before) * 100 if revenue_before else 0

            revenue_before_converted, revenue_after_converted = self._convert_to_target_currency(revenue_before, revenue_after)

            self.write({
                'total_changes': len(logs),
                'highest_increase_product_id': highest_increase_product,
                'highest_decrease_product_id': highest_decrease_product,
                'revenue_before': revenue_before,
                'revenue_after': revenue_after,
                'revenue_before_converted': revenue_before_converted,
                'revenue_after_converted': revenue_after_converted,
                'profitability': profitability,
                'product_ids': [(6, 0, logs.mapped('product_id').ids)],
            })
        except Exception as e:
            raise UserError(_("Error during report generation: %s") % e)

    def _get_sales_for_period(self, product, operator, date):
        """Helper method to fetch sales within a given period."""
        try:
            return self.env['sale.order.line'].search([
                ('product_id', '=', product.id),
                ('order_id.state', '=', 'sale'),
                ('order_id.date_order', operator, date)
            ])
        except Exception as e:
            raise UserError(_("Error fetching sales for product '%s': %s") % (product.display_name, e))

    def _convert_to_target_currency(self, revenue_before, revenue_after):
        """Helper method to convert revenue to the target currency."""
        try:
            if self.currency_id and self.currency_id != self.env.company.currency_id:
                target_currency_rate = self.currency_id.rate or 1
                return revenue_before * target_currency_rate, revenue_after * target_currency_rate
            return revenue_before, revenue_after
        except Exception as e:
            raise UserError(_("Error converting revenue to target currency: %s") % e)

    @api.model
    def create(self, vals):
        try:
            record = super(PriceChangeReport, self).create(vals)
            record.generate_report()
            return record
        except Exception as e:
            raise UserError(_("Error creating Price Change Report: %s") % e)

    def write(self, vals):
        try:
            res = super(PriceChangeReport, self).write(vals)
            if 'start_date' in vals or 'end_date' in vals or 'currency_id' in vals:
                self.generate_report()
            return res
        except Exception as e:
            raise UserError(_("Error updating Price Change Report: %s") % e)

    def action_generate_report(self):
        """Manually trigger the report generation."""
        try:
            self.ensure_one()
            self.generate_report()
        except Exception as e:
            raise UserError(_("Error manually generating report: %s") % e)

    def action_export_excel(self):
        """Export the report to Excel."""
        try:
            self.ensure_one()

            if not self.total_changes:
                self.generate_report()

            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet(_('Price Change Report'))

            bold = workbook.add_format({'bold': True})
            currency_format = workbook.add_format({'num_format': '#,##0.00'})

            worksheet.write(0, 0, _('Price Change Report'), bold)
            worksheet.write(1, 0, _('Start Date: %s') % format_date(self.env, self.start_date), bold)
            worksheet.write(2, 0, _('End Date: %s') % format_date(self.env, self.end_date), bold)
            worksheet.write(3, 0, _('Currency: %s') % self.currency_id.name, bold)

            worksheet.write(5, 0, _('Total Changes:'), bold)
            worksheet.write(5, 1, self.total_changes)
            worksheet.write(6, 0, _('Revenue Before:'), bold)
            worksheet.write(6, 1, self.revenue_before)
            worksheet.write(7, 0, _('Revenue After:'), bold)
            worksheet.write(7, 1, self.revenue_after)
            worksheet.write(8, 0, _('Revenue Before (Converted):'), bold)
            worksheet.write(8, 1, self.revenue_before_converted)
            worksheet.write(9, 0, _('Revenue After (Converted):'), bold)
            worksheet.write(9, 1, self.revenue_after_converted)
            worksheet.write(10, 0, _('Profitability Change (%):'), bold)
            worksheet.write(10, 1, self.profitability)
            worksheet.write(12, 0, _('Highest Increase Product:'), bold)
            worksheet.write(12, 1, self.highest_increase_product_id.display_name if self.highest_increase_product_id else _('N/A'))
            worksheet.write(13, 0, _('Highest Decrease Product:'), bold)
            worksheet.write(13, 1, self.highest_decrease_product_id.display_name if self.highest_decrease_product_id else _('N/A'))

            workbook.close()
            output.seek(0)

            attachment = self.env['ir.attachment'].create({
                'name': _('price_Change_Report.xlsx'),
                'type': 'binary',
                'datas': base64.b64encode(output.read()),
                'res_model': 'price.change.report',
                'res_id': self.id,
                'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            })

            return {
                'type': 'ir.actions.act_url',
                'url': '/web/content/%d?download=true' % attachment.id,
                'target': 'self',
            }
        except Exception as e:
            raise UserError(_("Error exporting to Excel: %s") % e)


    def action_export_pdf(self):
        """Export the report to PDF."""
        try:
            self.ensure_one()

            if not self.total_changes:
                self.generate_report()

            report_action = self.env.ref('zehntech_mass_price_update.price_change_report_pdf')

            if not report_action:
                raise UserError(_("Report action not found."))

            return report_action.report_action(self)
        except Exception as e:
            raise UserError(_("Error exporting to PDF: %s") % e)
