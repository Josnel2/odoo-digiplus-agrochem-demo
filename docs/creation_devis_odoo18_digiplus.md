# Creation du Devis dans le Module Ventes Odoo 18

## 1. Introduction

Dans Odoo 18, le devis est le premier document commercial officiel genere par le module Ventes. Il formalise la proposition faite au client a partir d'un besoin deja qualifie sur le plan commercial. Il contient les informations essentielles de l'offre : client, prestations ou produits, prix, taxes, validite et conditions commerciales.

Le devis n'est pas encore une commande client. Tant qu'il n'est pas accepte, il reste une proposition commerciale ouverte a la discussion. Il permet donc de cadrer l'offre, de la presenter clairement au client et de conserver une trace structurée des negociations avant engagement.

Dans l'environnement DigiPlus, le devis joue un role central car il doit couvrir aussi bien les ventes de services digitaux que les ventes ponctuelles de licences ou de materiel. Il doit etre clair pour le client, exploitable par les equipes internes et conforme au format de presentation DigiPlus.

## 2. Point de depart du devis

La creation du devis peut se faire de deux manieres.

### A. Depuis une opportunite CRM gagnee

Lorsqu'une opportunite devient suffisamment mature, ou dans le cas DigiPlus lorsqu'elle passe a l'etat `Gagne`, le systeme peut preparer automatiquement :

- le partenaire client ;
- le devis lie a l'opportunite.

Cette approche assure la continuite entre CRM et Vente. Le commercial retrouve deja un dossier rattache au bon client et complete ensuite les informations commerciales du devis.

### B. Creation manuelle depuis le module Ventes

Le commercial peut aussi creer directement un devis depuis le module Ventes, sans passer par une creation automatique issue du CRM.

Chemin Odoo :

```text
Ventes -> Devis -> Nouveau
```

Cette methode est utile pour :

- une vente creee directement par l'equipe commerciale ;
- un renouvellement de prestation ;
- une vente simple de licence ou de materiel ;
- un besoin ponctuel ne necessitant pas une reprise detaillee du pipeline CRM.

## 3. Informations principales a renseigner

Une fois le devis ouvert, plusieurs champs doivent etre verifies ou completes.

### Client

Le champ `Client` identifie le partenaire principal. C'est la base de toute la relation commerciale : nom de la societe, contact, historique, langue, conditions de paiement et documents lies.

### Adresse de facturation

L'adresse de facturation determine le destinataire administratif de la facture finale. Elle peut etre differente de l'adresse principale du client.

### Adresse de livraison

Ce champ est surtout utile si le devis inclut du materiel informatique ou un produit physique. Pour les prestations de services, il peut etre identique au client ou rester secondaire.

### Date du devis

La date du devis correspond a la date d'emission du document commercial. Elle permet de situer l'offre dans le temps.

### Date d'expiration ou validite

La date de validite indique jusqu'a quand l'offre reste valable. Elle encadre juridiquement et commercialement la proposition. Dans Odoo, cette date peut etre saisie manuellement ou derivee d'un modele de devis.

### Conditions de paiement

Ce champ precise comment le client doit regler :

- comptant ;
- a 30 jours ;
- acompte puis solde ;
- paiement trimestriel ou mensuel selon le contrat.

### Liste de prix

La liste de prix determine les regles tarifaires appliquees au devis. Elle peut varier selon le type de client, la devise, le pays ou la politique commerciale.

### Devise

La devise du devis est definie en fonction de la liste de prix ou du contexte commercial. Pour des ventes Microsoft 365 ou des prestations internationales, ce point peut etre important.

### Commercial responsable

Le commercial responsable porte le dossier et reste l'interlocuteur principal du client pour la proposition.

### Equipe commerciale

L'equipe commerciale permet de rattacher le devis a la bonne organisation interne pour le pilotage et le reporting.

### Reference client

La reference client peut etre utilisee si le client impose un numero interne, un bon de commande preliminaire ou un code projet.

## 4. Ajout des produits ou services

Le coeur du devis se trouve dans les lignes commerciales. Chaque ligne precise ce qui est vendu et a quel prix.

Pour chaque ligne, le commercial renseigne :

- le produit ou service ;
- la description commerciale ;
- la quantite ;
- le prix unitaire ;
- la remise eventuelle ;
- les taxes ;
- le total de ligne.

### Selection du produit ou service

Le commercial choisit un article du catalogue Odoo. Dans DigiPlus, il s'agit le plus souvent d'un service de type :

- prestation Odoo ERP ;
- structuration CRM ;
- developpement web ;
- formation ;
- support technique ;
- licence Microsoft 365 ;
- transformation digitale.

### Description commerciale

La description permet d'expliquer clairement le contenu de la ligne vendue. C'est cette zone qui sera lue par le client dans le PDF du devis. Elle doit donc etre explicite et orientee metier.

### Quantite

La quantite peut representer :

- un forfait ;
- un nombre de licences ;
- un nombre de jours ;
- un nombre de sessions ;
- un nombre d'equipements.

### Prix unitaire

Le prix unitaire est repris depuis la fiche produit ou saisi manuellement si le devis est ajuste au cas par cas.

### Remise

Une remise peut etre appliquee pour tenir compte d'un geste commercial, d'un pack, d'une phase pilote ou d'un volume negocie.

### Taxes

Les taxes s'appliquent a chaque ligne selon la configuration fiscale de l'entreprise et du client.

### Total de ligne

Odoo calcule automatiquement le total de ligne a partir de la quantite, du prix unitaire, de la remise et des taxes.

### Exemples adaptes a DigiPlus

- `Licence Microsoft 365` : quantite par utilisateur ou par abonnement.
- `Formation professionnelle` : quantite par session ou par groupe.
- `Prestation Odoo` : quantite en forfait ou en jours.
- `Site web` : lignes par lot de cadrage, design, developpement et mise en ligne.
- `Support mensuel` : quantite par mois ou par periode contractuelle.
- `Materiel informatique` : quantite par equipement vendu.

## 5. Calcul des montants

Odoo calcule automatiquement les montants du devis a mesure que les lignes sont saisies.

Les informations affichees dans la zone de total correspondent a :

- `Sous-total` : somme des lignes hors taxes ;
- `TVA` : montant total des taxes appliquees ;
- `Total TTC` : montant final toutes taxes comprises ;
- `Montant global du devis` : total final presente au client.

Dans la presentation DigiPlus, cette zone correspond directement aux blocs :

```text
Sous-total
TVA
Total
```

L'interet d'Odoo est d'eviter les calculs manuels et de garantir la coherence entre lignes, taxes et total general.

## 6. Termes et conditions

Les termes et conditions donnent au devis sa valeur contractuelle et operationnelle. Ils permettent d'encadrer la proposition au-dela des seuls montants.

Les points importants a faire apparaitre sont :

- la duree de validite de l'offre ;
- les modalites de paiement ;
- les delais d'execution ;
- les conditions de livraison si un produit physique est vendu ;
- les conditions d'annulation ou de report ;
- la mention `Bon pour accord`.

Dans le modele DigiPlus affiche, la section `TERMS AND CONDITIONS` a une place claire en bas de page. En pratique, Odoo permet d'alimenter cette zone via les conditions de vente, les notes du devis ou un modele de devis standardise.

## 7. Statuts du devis

### Statuts standards Odoo

Les statuts standards du devis permettent de suivre le cycle normal du document :

- `Brouillon` : devis en preparation ;
- `Envoye` : devis transmis au client ;
- `Commande client` : devis confirme apres acceptation ;
- `Annule` : devis abandonne ou cloture sans suite.

### Statut metier DigiPlus `x_decision_status`

En plus du statut standard, DigiPlus utilise un statut complementaire :

- `draft`
- `in_review`
- `sent`
- `approved`
- `won`

Ce statut sert a :

- suivre la decision commerciale interne ;
- savoir si le devis est encore en preparation, en revue, deja envoye, approuve ou gagne ;
- donner plus de visibilite a l'equipe commerciale et a la direction.

Ce double suivi est utile car un devis peut etre dans un etat standard Odoo simple, tout en ayant un niveau de maturite metier plus fin dans le pilotage DigiPlus.

## 8. Actions possibles sur le devis

Une fois cree, le devis peut faire l'objet de plusieurs actions dans Odoo :

- `Sauvegarder le devis` pour conserver le travail en cours ;
- `Envoyer par email` pour transmettre la proposition au client ;
- `Imprimer le PDF` pour generer le document commercial officiel ;
- `Modifier les lignes` pour ajuster contenu, quantites ou prix ;
- `Reviser le devis` si une nouvelle version est necessaire ;
- `Annuler le devis` si l'offre est abandonnee ;
- `Confirmer le devis` lorsque le client accepte l'offre.

Dans votre environnement, un modele d'email de proposition existe deja pour l'envoi commercial. Il peut servir de base a la demonstration client.

## 9. Document genere

Le document genere par le module Vente est le devis PDF. C'est lui qui sert de support officiel a la proposition commerciale envoyee au client.

Dans le cas DigiPlus, la maquette de reference affichee comporte notamment :

- le logo DigiPlus Consulting ;
- un titre de document en haut de page ;
- le numero du devis ;
- la date d'emission ;
- le bloc client ;
- un tableau des lignes ;
- le total ;
- les termes et conditions ;
- la signature `Bon pour accord` ;
- le message de fin `Merci de votre confiance` ;
- le footer de contact DigiPlus.

### Note sur la maquette fournie

L'image de reference utilise le titre `PROFORMA` et des libelles en anglais. Pour la documentation fonctionnelle du module Vente, le document cible est presente comme un `DEVIS`, avec la meme logique de zones, mais adapte en presentation francaise si necessaire.

### Correspondance entre le modele DigiPlus et Odoo

| Zone du devis | Champ ou donnee Odoo |
|---|---|
| Devis ndeg | Reference du devis (`name`) |
| Date du devis | Date du devis (`date_order`) |
| Validite du devis | Date d'expiration (`validity_date`) |
| Entreprise | Societe configuree dans Odoo |
| Client | Partenaire client (`partner_id`) |
| Adresse de facturation | Adresse facturee du partenaire (`partner_invoice_id`) |
| Adresse de livraison | Adresse de livraison (`partner_shipping_id`) |
| Description | Lignes de commande (`order_line.name`) |
| Prix | Prix unitaire (`price_unit`) |
| Quantite | Quantite vendue (`product_uom_qty`) |
| Total de ligne | Sous-total de ligne (`price_subtotal`) |
| Sous-total | Total hors taxes du devis |
| TVA | Taxes appliquees |
| Total | Montant total du devis (`amount_total`) |
| Termes et conditions | Conditions de vente / notes du devis |
| Signature | Acceptation client / validation formelle |
| Footer DigiPlus | Coordonnees de la societe dans la mise en page du rapport |

## 10. Cas de revision du devis

Si le client demande une modification, le devis reste dans une logique de negociation commerciale. Le commercial peut alors :

- modifier les lignes ;
- ajuster les prix ;
- modifier les quantites ;
- ajouter une remise ;
- corriger les conditions ;
- renvoyer le devis au client.

L'avantage d'Odoo est que le suivi commercial est conserve. Le dossier reste rattache au bon client, a la bonne opportunite et au bon commercial. La revision ne casse donc pas l'historique du processus.

## 11. Condition de passage a l'etape suivante

Le devis ne passe a l'etape suivante que lorsque le client accepte l'offre.

Le passage se formule ainsi :

```text
Devis accepte
-> Confirmation du devis
-> Commande client
```

Tant que cette confirmation n'est pas faite, le document reste une proposition commerciale. Une fois confirme, il devient une base ferme pour la facturation, le projet ou la livraison.

## 12. Tableau recapitulatif

| Etape | Action utilisateur | Donnee renseignee | Document genere | Statut | Etape suivante |
|---|---|---|---|---|---|
| 1 | Ouvrir une opportunite ou cliquer sur `Nouveau` | Opportunite ou contexte commercial | Brouillon de devis | Brouillon | Saisie du client |
| 2 | Renseigner le client | Client, adresses, reference | Devis en cours | Brouillon | Saisie des informations generales |
| 3 | Completer les informations generales | Date, validite, paiement, devise, commercial | Devis enrichi | Brouillon | Ajout des lignes |
| 4 | Ajouter les produits ou services | Description, quantite, prix, taxes, remise | Devis chiffre | Brouillon | Calcul des montants |
| 5 | Verifier les montants | Sous-total, TVA, total | Devis finalise | Brouillon | Ajout des conditions |
| 6 | Completer les termes et conditions | Validite, paiement, delais, bon pour accord | Devis pret a envoi | Brouillon / in_review | Envoi au client |
| 7 | Envoyer ou imprimer | Email, PDF | Devis PDF | Envoye / sent | Attente de retour client |
| 8 | Reviser si besoin | Ajustements commerciaux | Devis revise | Brouillon / in_review | Renvoi client |
| 9 | Confirmer apres accord | Validation finale | Commande client | Commande client / won | Projet / Stock / Facturation |

## 13. Mini-workflow du devis

```text
Opportunite CRM gagnee
-> Creation du devis
-> Ajout client
-> Ajout produits/services
-> Calcul prix et taxes
-> Ajout conditions
-> Envoi au client
-> Revision si besoin
-> Acceptation
-> Confirmation
```

Variante manuelle :

```text
Ventes
-> Devis
-> Nouveau
-> Saisie des informations
-> Envoi du devis
-> Acceptation
-> Confirmation
```

## 14. Resume operationnel

Odoo 18 permet a DigiPlus de creer rapidement un devis a partir d'une opportunite CRM ou directement depuis le module Ventes. Le commercial renseigne le client, les dates, les conditions de paiement et les lignes de produits ou de services. Odoo calcule automatiquement le sous-total, la TVA et le total. Le devis peut ensuite etre mis en forme en PDF selon la presentation DigiPlus, puis envoye au client par email. Si le client demande un ajustement, le devis peut etre revise sans perdre l'historique commercial. Tant que le client n'a pas accepte l'offre, le document reste un devis. Une fois l'accord obtenu, le commercial confirme le document et Odoo le transforme en commande client. Cette commande devient alors la base des flux suivants vers Projet, Stock ou Facturation.
