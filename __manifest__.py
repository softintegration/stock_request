# -*- coding: utf-8 -*- 
{'name': 'Stock request',
 'author': 'Soft-integration',
 'application': False,
 'installable': True,
 'auto_install': False,
 'qweb': [],
 'description': False,
 'images': [],
 'version': '1.0.1.5',
 'category': 'Stock',
 'demo': [],
 'depends': ['stock',
             'portal',
             'cancel_motif'],
 'data': [
     'security/ir.model.access.csv',
     'data/stock_request_sequences.xml',
     'views/stock_request_views.xml',
     'views/stock_picking_views.xml',
     'views/res_config_settings_views.xml',
 ],
 'license': 'LGPL-3',
 }
