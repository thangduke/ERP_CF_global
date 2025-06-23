{
    'name' : 'Nhân sự',
    'version' : '0.0.1',
    'sequence': -100,
    'category': 'Human Resources/Employee',
    'summary' : 'Quản lý thông tin nhân sự',
    'depends': ['web_hierarchy',
                'base_setup',
                'web',
                'mail',
    ],
    'data': [
        'security/employee_security.xml',
        'security/ir.model.access.csv',

        'views/employee_department_views.xml',
        'views/employee_base_views.xml',
        'views/employee_position_views.xml',
        'views/employee_orgchart_views.xml',
        
        'views/employee_type_views.xml',
        'views/position_type_views.xml',
    
        'wizard/change_main_info.xml',
        'wizard/change_extra_info.xml',
        'wizard/change_managers.xml',
    
        'data/employee_update_state.xml',

        'views/employee_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'Employee/static/src/scss/*',
            'Employee/static/src/fields/**/*',
            'Employee/static/src/views/*',
            'Employee/static/src/xml/*',
            'Employee/static/src/components/**/*',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}