{
    'name': "Đơn hàng1",
    'summary': """Đơn hàng1""",
    'description': """Phần mềm quản lý Đơn hàng1""",
    'author': "thanghuu.info",
    'category': 'Garment Order',  # chính là tên của category đã tạo
    'sequence': -100,
    'version': '1.0',
    'depends': ['web','mail','base',],
      'data': [
               'security/garment_order_security.xml',
               'security/ir.model.access.csv',

            #    'data/ir_sequence_po.xml',
            #    'data/ir_sequence_product_code.xml',
            #    'data/ir_sequence_warehouse_order_p.xml',
            #    'data/ir_sequence_material.xml',
            #    'data/ir_sequence_customer.xml',
            #    'data/ir_sequence_invoice.xml',
            #    'data/ir_sequence_material_color.xml',
            #    'data/ir_cron_data.xml',   

            #    'wizard/material_import_export_views.xml',
            #    'wizard/product_import_export_wizard_views.xml',
            #    'wizard/material_invoice_create_wizard_views.xml',
            #    'wizard/style_color_size_import_wizard_views.xml',
            #    'wizard/material_style_import_wizard_views.xml',
            #    'wizard/create_style_color_size_wizard_views.xml',
            #    'wizard/request_add_po_wizard_views.xml',
            #    'wizard/apply_material_style_color_size_wizard_views.xml',
            #    'wizard/product_price_calculation_wizard_views.xml',

            #     'report/ir_purchase_order_reports.xml',
            #     'report/ir_purchase_order_template.xml',
            #     'report/ir_price_calculation_reports.xml',
            #     'report/ir_price_calculation_template.xml',
                
               'views/customer_garment_views.xml',
               'views/factory_garment_views.xml',
               'views/supplier_garment_views.xml',
               
               'views/material_color_views.xml',
               'views/material_type_views.xml', 
               'views/material_color_set_views.xml', 
               'views/material_rate_views.xml',
               
               'views/garment_material_views.xml',
               'views/garment_program_views.xml',
               'views/garment_style_views.xml',
               'views/garment_colorcard_views.xml',
               'views/garment_colorway_views.xml',
               'views/garment_costing_views.xml',
               'views/garment_order_breakdown_views.xml',
               'views/garment_consumption_views.xml',
               'views/garment_size_views.xml',
               
               
               'views/garment_order_menus.xml',

    ], 
    'assets': {
    'web.assets_backend': [
            'garment_order/static/src/css/*',
            'garment_order/static/src/scss/*',
            'garment_order/static/src/js/material_color_matrix_field.js',
            'garment_order/static/src/xml/material_color_matrix_field.xml',

    ],
}, 
    'installable': True,
    'application': True,
    'auto_install': False, 

}