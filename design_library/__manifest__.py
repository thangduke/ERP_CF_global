{
    'name': 'Thư Viện Thiết Kế',
    'category': 'Product',
    'summary': 'Thư viện mẫu thiết kế may mặc',
    'author': "thangnghuu.info",
    'sequence': 4,
    'version': '1.0',
    'depends': ['web','mail','base',],
      'data': [
               'security/design_library_security.xml',
               'security/ir.model.access.csv',
               'views/design_library_views.xml',     
                        
               'views/design_library_menus.xml',


    ], 
    'assets': {
    'web.assets_backend': [
            'design_library/static/src/css/*',

    ],
}, 
    'installable': True,
    'application': True,
    'auto_install': False, 

}

