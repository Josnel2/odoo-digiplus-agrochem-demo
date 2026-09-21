# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProjectTask(models.Model):
    _inherit = 'project.task'

    # Hiérarchie WBS
    wbs_code = fields.Char(
        string='WBS Code', 
        compute='_compute_wbs_code', 
        store=True,
        help="Code Work Breakdown Structure, généré automatiquement."
    )
    is_milestone = fields.Boolean(
        string='Jalon', 
        default=False,
        help="Indique si la tâche est un jalon (durée de 0)."
    )
    
    # Dates et Durées MS Project
    # Note: Odoo standard utilise date_assign, date_deadline, planned_hours.
    # Pour MS Project, nous avons besoin de début, fin, durée (jours), travail (heures).
    msproject_start_date = fields.Datetime(string='Date de Début Prévue')
    msproject_finish_date = fields.Datetime(string='Date de Fin Prévue')
    msproject_duration = fields.Float(
        string='Durée (Jours)', 
        help="Durée en jours ouvrés."
    )
    msproject_work = fields.Float(
        string='Travail (Heures)', 
        help="Effort total en heures."
    )
    msproject_schedule_mode = fields.Selection([
        ('auto', 'Planifiée automatiquement'),
        ('manual', 'Planifiée manuellement')
    ], string='Mode de planification', default='auto',
       help="Automatique: les dates sont calculées par le moteur. Manuelle: les dates sont saisies par l'utilisateur.")

    predecessor_ids = fields.One2many(
        'project.task.dependency',
        'successor_id',
        string='Predecesseurs'
    )
    successor_ids = fields.One2many(
        'project.task.dependency',
        'predecessor_id',
        string='Successeurs'
    )
    assignment_ids = fields.One2many(
        'project.task.assignment',
        'task_id',
        string='Ressources Assignees'
    )

    @api.depends('parent_id', 'sequence', 'project_id.task_ids')
    def _compute_wbs_code(self):
        """
        Calcule le code WBS (ex: 1, 1.1, 1.1.2) en fonction de la hiérarchie
        et de la séquence de la tâche dans le projet.
        """
        for project in self.mapped('project_id'):
            root_tasks = self.env['project.task'].search([
                ('project_id', '=', project.id),
                ('parent_id', '=', False)
            ], order='sequence, id')
            
            def assign_wbs(tasks, prefix=''):
                for index, task in enumerate(tasks, start=1):
                    current_wbs = f"{prefix}{index}" if prefix else str(index)
                    if task in self:
                        task.wbs_code = current_wbs
                    children = task.child_ids.sorted(key=lambda c: (c.sequence, c.id))
                    if children:
                        assign_wbs(children, prefix=f"{current_wbs}.")
            
            assign_wbs(root_tasks)
            
    @api.onchange('is_milestone')
    def _onchange_is_milestone(self):
        if self.is_milestone:
            self.msproject_duration = 0.0

    def _get_working_calendar(self):
        self.ensure_one()
        if hasattr(self.project_id, 'resource_calendar_id') and self.project_id.resource_calendar_id:
            return self.project_id.resource_calendar_id
        return self.company_id.resource_calendar_id

    def recalculate_schedule(self):
        """
        Moteur de calcul des dates (Forward pass).
        Propage les dates dans la chaîne de dépendance.
        """
        from datetime import timedelta
        for task in self:
            if task.msproject_schedule_mode == 'manual':
                continue
            
            # 1. Calcul de la date de fin = debut + duree
            if task.msproject_start_date and task.msproject_duration is not None:
                calendar = task._get_working_calendar()
                if calendar and hasattr(calendar, 'plan_days'):
                    task.msproject_finish_date = calendar.plan_days(
                        task.msproject_duration + 1, 
                        task.msproject_start_date,
                        compute_leaves=True
                    )
                else:
                    task.msproject_finish_date = task.msproject_start_date + timedelta(days=task.msproject_duration)

            # 2. Propagation aux successeurs
            for dep in task.successor_ids:
                succ = dep.successor_id
                if succ.msproject_schedule_mode == 'manual':
                    continue
                
                # Traitement du type de lien (FS principalement ici pour simplifier)
                if dep.dependency_type == 'FS' and task.msproject_finish_date:
                    lag_td = timedelta(days=dep.lag_time)
                    new_start = task.msproject_finish_date + lag_td
                    
                    if not succ.msproject_start_date or succ.msproject_start_date < new_start:
                        succ.msproject_start_date = new_start
                        succ.recalculate_schedule()

