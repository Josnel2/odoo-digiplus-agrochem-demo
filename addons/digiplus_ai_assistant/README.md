# DigiPlus AI Assistant

Module Odoo 18 de generation de brouillons de projets via `POST /projects/generate`.

## Installation

Placez le module dans le chemin d'addons, actualisez la liste des applications puis installez **DigiPlus AI Assistant**. Il depend de `digiplus_project`. Attribuez les groupes *Utilisateur Assistant IA* et *Validateur Assistant IA*.

Configurez dans Parametres > DigiPlus IA l'URL FastAPI, le timeout et le modele Ollama. Valeurs initiales : `http://ai-service:8000`, 60 secondes, `qwen2.5:0.5b`.

## Utilisation

Ouvrez DigiPlus IA > Generer un projet, renseignez la demande, puis corrigez le brouillon. Un validateur approuve ensuite le brouillon et cree le projet reel. Les dates, priorites et livrables sont convertis vers les champs de `digiplus_project`.

## Limites MVP

Le service FastAPI/Ollama reste externe au module. L'affectation d'un role IA a un utilisateur Odoo est manuelle. Le client absent doit etre cree ou selectionne par un humain. Aucune suppression, facture, paiement, publication ou communication externe n'est automatisee.
