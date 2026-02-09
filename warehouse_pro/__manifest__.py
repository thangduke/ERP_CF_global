{
    'name': "Kho Vật Tư",
    'summary': """warehouse_pro""",
    'description': """Phần mềm quản lý kho vật tư""",
    'author': "thangnghuu.info",
    'category': 'Warehouse Pro',  # chính là tên của category đã tạo
    'sequence': -90,
    'version': '1.0',
    'depends': ['web','mail','base',],
      'data': [
                'security/warehouse_pro_security.xml',
                'security/ir.model.access.csv',
                
                'data/ir_sequence_receive.xml',
                'data/ir_sequence_delivery.xml',
                'data/ir_sequence_production_list.xml',
                
                'wizard/assign_shelf_wizard_views.xml',
                'wizard/delivery_style_wizard_views.xml',


                
                'report/ir_material_receive_reports.xml',
                'report/ir_material_receive_template.xml',
                'report/ir_material_delivery_reports.xml',
                'report/ir_material_delivery_template.xml',
                
                'views/store_list_views.xml',
                'views/material_receive_views.xml',
                'views/shelf_list_views.xml',
                'views/material_receive_line_views.xml',
                'views/material_delivery_views.xml',
                
                'views/warehouse_tag_views.xml',
                'views/shelf_level_views.xml',
                'views/material_delivery_line_views.xml',
                'views/production_list_views.xml',
                'views/stock_quantity_adjustment_views.xml',
                'views/material_stock_card_views.xml',
                
                'views/stock_dashboard_views.xml',
                'views/material_transfer_views.xml',
                
                'views/warehouse_pro_menus.xml',
    ], 
    'assets': {
    'web.assets_backend': [
            'warehouse_pro/static/src/css/*',
            'warehouse_pro/static/src/scss/*',

            'warehouse_pro/static/src/xml/*',
            'warehouse_pro/static/src/js/*',

            'warehouse_pro/static/src/components/stock_dashboard.scss',
            'warehouse_pro/static/src/components/stock_dashboard.js',
            'warehouse_pro/static/src/components/stock_dashboard.xml',
            'https://cdn.jsdelivr.net/npm/chart.js',
        ],
    }, 
    'installable': True,
    'application': True,
    'auto_install': False, 

}