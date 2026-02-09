{
    'name': 'Quản lý tài sản',
    'version': '1.0',
    'summary': 'A professional module to manage company assets',
    'description': """
        This module allows for comprehensive management of company assets,
        including tracking, categorization, and reporting.
    """,
    'author': "thangnghuu.info",
    'sequence': -120,
    'version': '1.0',
    'category': 'Internal',
    'depends': ['base', 'mail', 'web'],
    'data': [
        'security/asset_management_pro_security.xml',
        'security/ir.model.access.csv',
        
        'data/ir_sequence_asset.xml',
        'views/asset_asset_views.xml',

        
        'views/asset_category_views.xml',
        'views/asset_type_views.xml',
        'views/asset_location_views.xml',
        'views/asset_status_views.xml',
        'views/asset_activity_history_views.xml',
        'views/asset_usage_views.xml',
        
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}