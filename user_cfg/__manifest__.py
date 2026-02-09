{
    'name': 'Tài khoản',
    'version': '1.0.0',
    'author': 'ThangNH',
    'category': 'Administration/Tài khoản',
    'sequence': 3, 
    'summary': 'Quản lý tài khoản',
    'depend': ['base'],
    'data': [     
        
        'security/ir.model.access.csv',
        'security/res_users_security.xml',
          
        'views/usercfg_account_view.xml',
        'views/usercfg_access_right_view.xml',
        'views/usercfg_menus.xml',
    ],
    'application': True,
    'auto_instal': False,
    'license': 'LGPL-3',
}
