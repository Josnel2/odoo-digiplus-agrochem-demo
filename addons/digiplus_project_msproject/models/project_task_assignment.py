# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProjectTaskAssignment(models.Model):
    _name = 'project.task.assignment'
    _description = 'Assignation de Ressource MS Project'

    task_id = fields.Many2one(
        'project.task', 
        string='Tache', 
        required=True, 
        ondelete='cascade'
    )
    # Dans une version complete, la ressource pourrait etre un equipement ou un cout.
    # Ici, nous nous basons sur les employes pour le "Travail" (Work).
    resource_id = fields.Many2one(
        'hr.employee', 
        string='Ressource', 
        required=True,
        ondelete='restrict'
    )
    
    units = fields.Float(
        string='Unites (%)', 
        default=100.0,
        help="Pourcentage d'allocation de la ressource sur cette tache."
    )
    work = fields.Float(
        string='Travail (Heures)', 
        default=0.0,
        help="Effort prevu par cette ressource sur cette tache."
    )

    @api.onchange('units', 'task_id.msproject_duration')
    def _onchange_units_duration(self):
        """
        Calcul du travail de base: Travail = Duree(jours) * 8h * Unites(%)
        """
        for record in self:
            if record.task_id.msproject_duration and record.units:
                # Supposons 8 heures par jour ouvré par defaut
                record.work = record.task_id.msproject_duration * 8 * (record.units / 100.0)
