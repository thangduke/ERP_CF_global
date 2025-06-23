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
               'data/ir_sequence_data.xml',
               'data/ir_sequence_delivery.xml',
               'wizard/warehouse_stock_summary_wizard_views.xml',
               
               'views/store_list_views.xml',
               'views/material_receive_views.xml',
               'views/shelf_list_views.xml',
                'views/shelf_material_line_views.xml',
                #'views/material_stock_views.xml',
                'views/material_delivery_views.xml',
               'views/warehouse_pro_menus.xml',


    ], 
    'assets': {
    'web.assets_backend': [
            'warehouse_pro/static/src/css/*',
            'warehouse_pro/static/src/scss/*',


    ],
}, 
    'installable': True,
    'application': True,
    'auto_install': False, 

}

