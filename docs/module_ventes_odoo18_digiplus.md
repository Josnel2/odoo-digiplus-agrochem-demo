# Cadrage General du Module Ventes Odoo 18

## 1. Introduction

Le module Vente est le point de bascule entre l'intention commerciale et l'execution operationnelle. Une fois que l'opportunite a ete qualifiee dans le CRM, le besoin n'est plus seulement commercial : il doit etre formalise, chiffre, valide par le client, puis transforme en commande exploitable par les autres modules Odoo.

Dans Odoo 18, le module Vente joue donc un role de pivot. Il structure l'offre, encadre les conditions commerciales, porte le document de reference remis au client et declenche les flux suivants vers la facturation, le projet ou le stock selon la nature de ce qui est vendu.

Dans l'environnement DigiPlus, ce role est encore plus important car l'activite repose majoritairement sur des prestations de services digitaux : ERP Odoo, CRM, developpement web, formation, support, licences Microsoft 365 et prestations de transformation digitale. Le module Vente doit donc a la fois servir d'outil de proposition commerciale et de point de depart pour l'execution des prestations.

## 2. Position du module Vente dans le workflow global

Le module Vente s'insere dans la chaine suivante :

```text
CRM
-> Opportunite gagnee
-> Ventes
-> Devis
-> Commande client
-> Facturation / Projet / Stock
-> Comptabilite
```

Le CRM identifie et qualifie l'opportunite. Le module Vente prend ensuite le relais pour produire une offre formelle et la convertir en commande client. A partir de cette commande, Odoo oriente l'execution vers le bon module aval :

- `Projet` pour les prestations de services.
- `Stock` pour les produits physiques ou materiels.
- `Facturation` pour les ventes facturables directement.

## 3. Role du module Vente

Le module Vente sert a :

- formaliser l'offre commerciale envoyee au client ;
- chiffrer les produits et services ;
- definir la validite de l'offre ;
- presenter les quantites, prix, taxes, remises et conditions ;
- obtenir l'accord du client ;
- transformer le devis en commande client ;
- declencher les flux avals vers la facturation, le projet ou le stock.

Autrement dit, le module Vente ne se limite pas a produire un devis. Il constitue le cadre contractuel et operationnel de la vente avant l'execution.

## 4. Point d'entree apres CRM

Le module Vente commence lorsqu'une opportunite CRM est suffisamment mature pour etre convertie en proposition commerciale. Selon l'organisation, ce point d'entree peut se faire a partir d'une opportunite qualifiee, en negociation, ou deja marquee comme gagnee.

Dans le cas DigiPlus, le passage de l'opportunite a l'etat `Gagne` peut preparer automatiquement deux elements essentiels :

- le partenaire client s'il n'existe pas encore ;
- le devis lie a l'opportunite.

Ce mecanisme permet d'eviter la ressaisie et d'assurer la continuite entre CRM et Vente. Le commercial reprend alors un devis deja rattache au bon client et a la bonne opportunite, qu'il n'a plus qu'a completer, verifier et envoyer.

## 5. Perimetre fonctionnel du module Vente

Le module Vente gere principalement les objets et informations suivants :

- `Clients` : identification du client, contact, adresses de facturation et de livraison.
- `Produits et services` : catalogue commercial des articles vendables.
- `Devis` : document commercial principal avant validation.
- `Lignes de devis` : detail des produits ou prestations proposes.
- `Prix` : prix unitaire, politique tarifaire, montant total.
- `Quantites` : nombre d'unites, jours, heures, licences ou forfaits.
- `Taxes` : TVA et regles fiscales appliquees aux lignes.
- `Remises` : reductions commerciales eventuelles.
- `Conditions de paiement` : acomptes, echeances, reglements a terme.
- `Validite du devis` : date limite d'acceptation de l'offre.
- `Termes et conditions` : clauses commerciales et remarques contractuelles.
- `Statut du devis` : niveau d'avancement du document dans le processus de vente.
- `Commande client` : document confirme, base de l'execution avale.

Le module Vente centralise donc tous les parametres commerciaux qui doivent etre valides avant demarrage operationnel.

## 6. Documents generes dans le module Vente

Le module Vente genere plusieurs documents utiles au cycle commercial :

### Devis

Le devis est le document de reference de l'offre commerciale. Il contient le client, les lignes de vente, les quantites, les prix, les taxes, la validite et les conditions de paiement.

### PDF de devis

Le devis peut etre edite en PDF pour envoi au client, validation interne ou archivage commercial. C'est souvent la version partagee officiellement.

### Email d'envoi du devis

Depuis Odoo, le commercial peut envoyer le devis par email directement au client. Cela permet de garder l'historique d'envoi dans le dossier commercial.

### Version revisee du devis

Si le client demande une modification, le devis peut etre corrige puis renvoye. Selon la configuration, cela prend la forme d'une mise a jour du devis existant ou d'une revision successive du document.

### Commande client

Quand le devis est accepte puis confirme, il devient une commande client. Ce document confirme engage alors l'execution des flux avals.

## 7. Statuts importants

### Statuts standards Odoo

Les statuts standards du module Vente servent a suivre la progression normale du document :

- `Devis brouillon` : le devis est en preparation.
- `Devis envoye` : le devis a ete transmis au client.
- `Commande client confirmee` : le devis a ete accepte et confirme.
- `Devis annule` : le devis a ete abandonne ou clos sans suite.

Ces statuts portent la logique standard Odoo et pilotent les actions disponibles sur le document.

### Statut metier DigiPlus

En plus du statut standard, DigiPlus utilise un statut complementaire `x_decision_status` avec les valeurs suivantes :

- `draft`
- `in_review`
- `sent`
- `approved`
- `won`

Ce statut metier ne remplace pas l'etat standard Odoo. Il sert a piloter la decision commerciale interne et a mieux suivre le niveau de maturite reel du dossier. Il permet par exemple de distinguer :

- un devis techniquement cree mais pas encore relu ;
- un devis en cours de validation interne ;
- un devis deja envoye ;
- un devis approuve sur le plan commercial ;
- un dossier considere comme gagne.

Ce statut complementaire est utile pour la gouvernance commerciale, les arbitrages de direction et le reporting.

## 8. Sorties possibles du module Vente

Une fois la commande client confirmee, le module Vente peut ouvrir trois grandes trajectoires.

### A. Vente de service

```text
Commande client
-> Projet / taches / jalons si necessaire
-> Facturation
```

Ce cas correspond aux prestations ERP, CRM, web, consulting, formation ou support. La commande devient la base de l'execution de service. Selon la configuration, elle peut alimenter un projet, des taches, des feuilles de temps ou des jalons facturables.

### B. Vente de produit physique

```text
Commande client
-> Stock / livraison
-> Facturation
```

Ce cas s'applique aux materiels ou equipements informatiques. La commande genere alors un flux logistique : preparation, livraison, puis facturation selon la politique retenue.

### C. Vente simple ou licence

```text
Commande client
-> Facturation directe
```

Ce cas concerne les ventes qui ne necessitent ni projet detaille ni livraison physique, par exemple une licence immaterielle, une prestation simple ou un forfait directement facturable.

## 9. Cas DigiPlus

### Vente de service ERP

Le devis porte generalement un forfait d'implementation, de parametrage, d'accompagnement et parfois de formation. Une fois confirme, il peut ouvrir un projet et preparer la facturation selon le planning commercial retenu.

### Vente de licence Microsoft 365

La vente peut etre geree comme une ligne de service ou de licence immaterielle. Le besoin principal du module Vente est ici de formaliser l'offre, les quantites, les periodicites et les conditions tarifaires avant facturation.

### Vente de formation

Le devis formalise le nombre de sessions, le nombre de participants, le format et le prix. Une fois confirme, il peut etre facture directement ou rattache a une prestation plus large.

### Vente de site web

Le devis structure les lots vendus : cadrage, design, developpement, integration, recette, mise en ligne. La commande peut ensuite alimenter un projet de livraison.

### Vente de support recurrent

Le devis sert a encadrer la duree, le perimetre, le niveau de service et le montant du support. Une fois confirme, il peut alimenter une facturation repetitive ou periodique selon l'organisation retenue.

### Vente occasionnelle de materiel informatique

Le devis peut inclure du materiel en complement d'un projet ou d'un besoin ponctuel. Dans ce cas, la commande client doit preparer le flux de livraison dans Stock avant la facturation finale.

## 10. Tableau recapitulatif

| Element | Role dans le module Vente | Statut possible | Module suivant |
|---|---|---|---|
| Opportunite gagnee | Point d'entree commercial apres CRM | Gagnee | Vente |
| Client | Porteur du contrat commercial | Actif / qualifie | Vente |
| Produit ou service | Element vendu et chiffre | Vendable / configure | Vente |
| Devis | Offre commerciale formelle | Brouillon / envoye / annule | Vente |
| Lignes de devis | Detail des prestations ou articles | En preparation / validees | Vente |
| Validite du devis | Limite temporelle de l'offre | Valide / expire | Vente |
| Statut metier `x_decision_status` | Suivi interne de la decision commerciale | `draft`, `in_review`, `sent`, `approved`, `won` | Vente |
| Commande client | Devis confirme et engageant | Confirmee | Projet / Stock / Facturation |
| Vente de service | Preparation de l'execution de prestation | A planifier / en cours | Projet puis Facturation |
| Vente de produit physique | Preparation de la livraison | A livrer / livre | Stock puis Facturation |
| Vente simple ou licence | Flux commercial sans projet ni stock detaille | A facturer | Facturation |

## 11. Mini-workflow textuel

```text
CRM qualifie
-> Creation du devis
-> Envoi au client
-> Acceptation
-> Confirmation
-> Commande client
-> Projet / Stock / Facturation
```

Dans la variante DigiPlus automatisee, le point de depart peut aussi etre formule ainsi :

```text
Opportunite gagnee
-> Preparation automatique du partenaire et du devis
-> Completion du devis
-> Envoi au client
-> Validation
-> Commande client
-> Projet / Stock / Facturation
```

## 12. Resume operationnel

Le module Vente d'Odoo 18 commence apres la qualification commerciale et transforme une opportunite en offre formelle. Il permet au commercial de preparer un devis clair, chiffre et date, puis de l'envoyer au client. Une fois l'accord obtenu, le devis est confirme et devient une commande client. Cette commande constitue le document de reference pour l'execution du dossier. Si la vente concerne une prestation, elle peut ouvrir un flux vers Projet. Si elle concerne un produit physique, elle declenche la livraison via Stock. Si elle concerne une licence ou une vente simple, elle peut partir directement en facturation. Le module Vente assure donc la continute entre le besoin commercial et l'execution interne. Dans DigiPlus, il joue un role central car il structure les ventes de services digitaux tout en preparant les flux administratifs et operationnels.
