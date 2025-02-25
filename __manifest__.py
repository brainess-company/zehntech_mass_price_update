{
    'name': 'Mass Price Update',
    'description': """Mass Price Update  module to efficiently update product prices and costs in bulk based on categories, attributes, tags, or specific selections""",
    'summary':"""This module allows you to manage and modify pricing in bulk with ease,
                 ensuring that your pricing strategy remains competitive and aligned with business objectives.
           .""",
    'version': '16.0.1.0.0',
    'category': 'Services',
    "author": "Zehntech Technologies Inc.",
    "company": "Zehntech Technologies Inc.",
    "maintainer": "Zehntech Technologies Inc.",
    "contributor": "Zehntech Technologies Inc.",
    "website": "https://www.zehntech.com/",
    "support": "odoo-support@zehntech.com",
    'depends': [ 'product', 'stock', 'sale','sale_management','account'],
    'data': [
        'security/mass_price_update_groups.xml',
        'security/ir.model.access.csv',
        'wizard/mass_price_update_views.xml',
        'views/mass_price_update_log_views.xml',
        'views/price_change_report_template.xml',
        'views/price_change_report_views.xml',
        'views/report.xml',
        'data/demo_user.xml',
    ],
    
    'i18n': [
        'i18n/de_CH.po',    # German translation file
        'i18n/es.po',      # Spanish translation file
        'i18n/fr.po',      # French translation file
        'i18n/ja_JP.po',   # Japanese translation file
    ],
    "images": [
        "static/description/banner.png",
    ],
    "license": "OPL-1",
    "installable": True,
    "application": True,
    "auto_install": False,
    "price": 00.00, 
    "currency": "USD"
}