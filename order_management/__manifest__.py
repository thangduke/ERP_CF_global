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
               'data/ir_sequence_product_code.xml',
               'data/ir_sequence_warehouse_order_p.xml',
               'data/ir_sequence_material.xml',
               'data/ir_sequence_customer.xml',
               'data/ir_sequence_invoice.xml',
               'data/ir_sequence_material_color.xml',
               'data/ir_cron_data.xml',

               'wizard/material_import_export_views.xml',
               'wizard/product_import_export_wizard_views.xml',
               'wizard/material_invoice_create_wizard_views.xml',
               'wizard/style_color_size_import_wizard_views.xml',
               'wizard/material_style_import_wizard_views.xml',
               'wizard/create_style_color_size_wizard_views.xml',
               'wizard/request_add_po_wizard_views.xml',
               'wizard/apply_material_style_color_size_wizard_views.xml',
               'wizard/product_price_calculation_wizard_views.xml',

                'report/ir_purchase_order_reports.xml',
                'report/ir_purchase_order_template.xml',
                'report/ir_price_calculation_reports.xml',
                'report/ir_price_calculation_template.xml',
                
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
               'views/material_norm_line_views.xml',
               'views/program_customer_line_views.xml',
                                        
               'views/program_customer_views.xml',
               'views/product_code_views.xml',
               'views/product_size_views.xml',
               'views/product_color_views.xml',
               'views/product_color_size_views.xml',            
               'views/product_price_calculation_views.xml',
               'views/material_rate_views.xml',
           
               'views/order_management_menus.xml',

    ], 
    'assets': {
    'web.assets_backend': [
            'order_management/static/src/css/*',
            'order_management/static/src/scss/*',
            'order_management/static/src/js/material_color_matrix_field.js',
            'order_management/static/src/xml/material_color_matrix_field.xml',

    ],
}, 
    'installable': True,
    'application': True,
    'auto_install': False, 

}