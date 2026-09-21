# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProjectTaskDependency(models.Model):
    _name = 'project.task.dependency'
    _description = 'Dependance de Tache MS Project'

    predecessor_id = fields.Many2one(
        'project.task', 
        string='Predecesseur', 
        required=True, 
        ondelete='cascade'
    )
    successor_id = fields.Many2one(
        'project.task', 
        string='Successeur', 
        required=True, 
        ondelete='cascade'
    )
    
    dependency_type = fields.Selection([
        ('FS', 'Fin a Debut (FS)'),
        ('SS', 'Debut a Debut (SS)'),
        ('FF', 'Fin a Fin (FF)'),
        ('SF', 'Debut a Fin (SF)')
    ], string='Type de lien', default='FS', required=True)
    
    lag_time = fields.Float(
        string='Decalage (Jours)', 
        default=0.0,
        help="Decalage en jours. Positif = retard (Lag), Negatif = anticipation (Lead)."
    )

    _sql_constraints = [
        ('predecessor_successor_uniq', 'unique(predecessor_id, successor_id)', 'Une dependance entre ces deux taches existe deja !'),
        ('no_self_dependency', 'check(predecessor_id != successor_id)', 'Une tache ne peut pas dependre d elle-meme.')
    ]
