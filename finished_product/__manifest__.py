{
    'name': 'Kho Thành Phẩm',
    'category': 'Warehouse',
    'summary': 'Quản lý kho thành phẩm may mặc',
    'author': "thangnghuu.info",
    'sequence': 3,
    'version': '1.0',
    'depends': ['web','mail','base',],
      'data': [
               'security/finished_product_security.xml',
               'security/ir.model.access.csv',
               'views/finished_product_views.xml',
               
                'views/finished_product_menus.xml',


    ], 
    'assets': {
    'web.assets_backend': [
            'finished_product/static/src/css/*',

    ],
}, 
    'installable': True,
    'application': True,
    'auto_install': False, 

}

