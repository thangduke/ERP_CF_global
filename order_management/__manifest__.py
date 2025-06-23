{
    'name': "Đơn hàng",
    'summary': """Đơn hàng""",
    'description': """Phần mềm quản lý Đơn hàng""",
    'author': "thangnghuu.info",
    'category': 'Order Management',  # chính là tên của category đã tạo
    'sequence': -100,
    'version': '1.0',
    'depends': ['web','mail','base',],
      'data': [
               'security/order_management_security.xml',
               'security/ir.model.access.csv',

               'data/ir_sequence_po.xml',
               
               'wizard/material_import_export_views.xml',
               'wizard/program_import_export_views.xml',
               'wizard/product_import_export_wizard_views.xml',
                       

               'views/customer_cf_views.xml',
               'views/factory_partner_views.xml',
               'views/supplier_partner_views.xml',
               'views/warehouse_order_views.xml',
               
               'views/material_color_views.xml',
               'views/material_invoice_views.xml', 
               'views/material_line_views.xml',
               'views/material_type_views.xml', 
               'views/material_color_set_views.xml', 
               'views/material_purchase_order_views.xml', 
                                        
               'views/progarm_customer_views.xml',
               'views/product_code_views.xml',
               'views/product_size_views.xml',
               'views/product_color_views.xml',
               'views/product_color_size_views.xml',
               
               
               'views/order_management_menus.xml',



    ], 
    'assets': {
    'web.assets_backend': [
            'order_management/static/src/css/*',
            'order_management/static/src/scss/*',

    ],
}, 
    'installable': True,
    'application': True,
    'auto_install': False, 

}

