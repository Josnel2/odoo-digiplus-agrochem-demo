# -*- coding: utf-8 -*-
import base64
import xml.etree.ElementTree as ET
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ImportMSProjectWizard(models.TransientModel):
    _name = 'import.msproject.wizard'
    _description = 'Assistant Importation MS Project XML'

    project_name = fields.Char(string='Nom du Projet Odoo', required=True)
    msproject_file = fields.Binary(string='Fichier XML MS Project', required=True)
    file_name = fields.Char(string='Nom du fichier')

    def action_import(self):
        """
        Lit le fichier XML MS Project (2013-2024), extrait les donnees
        et reconstruit l'arbre dans Odoo (Projet, Taches, Dependances).
        """
        self.ensure_one()
        if not self.msproject_file:
            raise UserError(_("Veuillez charger un fichier XML."))
            
        try:
            xml_data = base64.b64decode(self.msproject_file)
            root = ET.fromstring(xml_data)
        except Exception as e:
            raise UserError(_("Erreur lors de la lecture du fichier XML : %s" % str(e)))

        # L'espace de nom (namespace) par defaut de MS Project
        ns = {'ns': root.tag.split('}')[0].strip('{')} if '}' in root.tag else {}
        def get_tag(tag):
            return f"ns:{tag}" if ns else tag

        # 1. Creer le Projet Odoo
        project = self.env['project.project'].create({
            'name': self.project_name,
            'description': "Importe depuis MS Project",
        })

        # 2. Dictionnaire pour mapper les UID MS Project aux ID Odoo
        task_uid_mapping = {}

        # 3. Import des Taches
        tasks_node = root.find(get_tag('Tasks'), ns)
        if tasks_node is not None:
            # Trier par OutlineNumber pour garantir la creation du parent avant l'enfant
            for task_node in tasks_node.findall(get_tag('Task'), ns):
                uid = task_node.find(get_tag('UID'), ns)
                name = task_node.find(get_tag('Name'), ns)
                
                # Ignorer la tache racine projet "0" (MS Project l'ajoute souvent)
                if uid is None or name is None or uid.text == '0':
                    continue

                # Extraction des donnees de base
                is_milestone = task_node.find(get_tag('Milestone'), ns)
                duration_str = task_node.find(get_tag('Duration'), ns)
                wbs = task_node.find(get_tag('WBS'), ns)
                outline_level = task_node.find(get_tag('OutlineLevel'), ns)
                parent_uid = task_node.find(get_tag('ParentTaskUID'), ns)

                # TODO: Convertir duration_str (format PT8H) en heures/jours
                # TODO: Mapper les dates de debut et de fin
                
                # Determiner le parent Odoo
                parent_id = False
                if parent_uid is not None and parent_uid.text in task_uid_mapping:
                    parent_id = task_uid_mapping[parent_uid.text]

                # Creation de la tache Odoo
                new_task = self.env['project.task'].create({
                    'name': name.text,
                    'project_id': project.id,
                    'parent_id': parent_id,
                    'is_milestone': is_milestone.text == '1' if is_milestone is not None else False,
                    # Les dates et la duree reelle demanderont un parsing detaille iso8601 (PT8H)
                    'msproject_schedule_mode': 'auto',
                })
                
                # Stocker le mapping
                task_uid_mapping[uid.text] = new_task.id

        # 4. Import des Liaisons (PredecessorLinks)
        # MS Project stocke les liens sous <Task><PredecessorLink>
        for task_node in tasks_node.findall(get_tag('Task'), ns):
            uid = task_node.find(get_tag('UID'), ns)
            if uid is None or uid.text not in task_uid_mapping:
                continue
                
            successor_id = task_uid_mapping[uid.text]
            
            for pred_link in task_node.findall(get_tag('PredecessorLink'), ns):
                pred_uid = pred_link.find(get_tag('PredecessorUID'), ns)
                link_type_node = pred_link.find(get_tag('Type'), ns)
                lag_node = pred_link.find(get_tag('LinkLag'), ns)
                
                if pred_uid is not None and pred_uid.text in task_uid_mapping:
                    predecessor_id = task_uid_mapping[pred_uid.text]
                    
                    # MS Project Types: 0=FF, 1=FS, 2=SF, 3=SS
                    # Odoo types que nous avons definis : FS, SS, FF, SF
                    link_type_map = {'0': 'FF', '1': 'FS', '2': 'SF', '3': 'SS'}
                    dep_type = 'FS'
                    if link_type_node is not None and link_type_node.text in link_type_map:
                        dep_type = link_type_map[link_type_node.text]
                        
                    # Lag in tenths of a minute (e.g., 4800 = 480 minutes = 1 day if 8h/day)
                    lag_days = 0.0
                    if lag_node is not None:
                        try:
                            lag_days = float(lag_node.text) / 4800.0
                        except ValueError:
                            pass

                    self.env['project.task.dependency'].create({
                        'predecessor_id': predecessor_id,
                        'successor_id': successor_id,
                        'dependency_type': dep_type,
                        'lag_time': lag_days
                    })

        # 5. Import des Ressources et Assignations
        resource_mapping = {}
        resources_node = root.find(get_tag('Resources'), ns)
        if resources_node is not None:
            for res_node in resources_node.findall(get_tag('Resource'), ns):
                res_uid = res_node.find(get_tag('UID'), ns)
                res_name = res_node.find(get_tag('Name'), ns)
                if res_uid is not None and res_name is not None and res_name.text:
                    # Recherche ou creation d'un employe correspondant
                    employee = self.env['hr.employee'].search([('name', 'ilike', res_name.text)], limit=1)
                    if not employee:
                        employee = self.env['hr.employee'].create({'name': res_name.text})
                    resource_mapping[res_uid.text] = employee.id

        assignments_node = root.find(get_tag('Assignments'), ns)
        if assignments_node is not None:
            for ass_node in assignments_node.findall(get_tag('Assignment'), ns):
                task_uid = ass_node.find(get_tag('TaskUID'), ns)
                res_uid = ass_node.find(get_tag('ResourceUID'), ns)
                units = ass_node.find(get_tag('Units'), ns)
                work = ass_node.find(get_tag('Work'), ns)
                
                if task_uid is not None and task_uid.text in task_uid_mapping and res_uid is not None and res_uid.text in resource_mapping:
                    # Conversion units (e.g., 1 = 100%, 0.5 = 50%)
                    unit_val = 100.0
                    if units is not None:
                        try:
                            unit_val = float(units.text) * 100
                        except ValueError:
                            pass
                    
                    self.env['project.task.assignment'].create({
                        'task_id': task_uid_mapping[task_uid.text],
                        'resource_id': resource_mapping[res_uid.text],
                        'units': unit_val,
                    })

        # Declencher un recalcul global du planning
        if task_uid_mapping:
            all_tasks = self.env['project.task'].browse(list(task_uid_mapping.values()))
            all_tasks.recalculate_schedule()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Projet Importe',
            'view_mode': 'form',
            'res_model': 'project.project',
            'res_id': project.id,
        }
