# Configuration email Odoo

Le projet fournit deux scripts:

- `scripts/configure_outgoing_mail.sh`: cree ou met a jour le serveur SMTP sortant Odoo et les parametres email de base.
- `scripts/send_test_mail.sh`: envoie un email de test reel depuis Odoo.

## Variables a renseigner dans `.env`

- `DIGIPLUS_SMTP_HOST`
- `DIGIPLUS_SMTP_PORT`
- `DIGIPLUS_SMTP_USER`
- `DIGIPLUS_SMTP_PASSWORD`
- `DIGIPLUS_SMTP_ENCRYPTION` (`none`, `starttls`, `ssl`)
- `DIGIPLUS_SMTP_FROM_FILTER`
- `DIGIPLUS_COMPANY_EMAIL`
- `DIGIPLUS_ALIAS_DOMAIN`
- `DIGIPLUS_DEFAULT_FROM_ALIAS`
- `DIGIPLUS_CATCHALL_ALIAS`
- `DIGIPLUS_BOUNCE_ALIAS`

## Configuration

Depuis la racine du projet:

```bash
./scripts/configure_outgoing_mail.sh adoo-digiplus-consulting
```

Le script:

- demarre le conteneur Odoo si necessaire
- configure un enregistrement `ir.mail_server`
- applique le `FROM filtering`
- configure les parametres `mail.catchall.domain`, `mail.default.from`, `mail.catchall.alias` et `mail.bounce.alias` si `DIGIPLUS_ALIAS_DOMAIN` est renseigne
- teste la connexion SMTP

## Test d'envoi

```bash
./scripts/send_test_mail.sh destinataire@example.com "Test Odoo DigiPlus" adoo-digiplus-consulting
```

## Prerequis DNS

Pour que les emails passent en production, il faut aussi que le domaine d'envoi soit correctement configure chez le provider:

- SPF
- DKIM
- DMARC

Si votre provider impose une adresse exacte d'expedition, utilisez la meme adresse dans:

- `DIGIPLUS_SMTP_USER`
- `DIGIPLUS_COMPANY_EMAIL`
- `DIGIPLUS_TEST_EMAIL_FROM`

et faites correspondre `DIGIPLUS_SMTP_FROM_FILTER` a cette adresse exacte ou a son domaine.
