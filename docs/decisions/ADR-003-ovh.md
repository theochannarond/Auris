# ADR-003 — OVHcloud plutôt qu'AWS ou Google Cloud

| | |
|---|---|
| **Statut** | Acceptée — en production sur `https://aurishetic.fr` |
| **Date de la décision** | Juillet 2026 |
| **Date de rédaction** | 26 août 2026 |
| **Décideurs** | Enzo Bandinu, Théo Channarond, Mathis Fonbonne, Lydie Havugimana |
| **Périmètre** | Hébergement applicatif, stockage objet, sauvegardes |

> **Note de méthode.** Document rédigé a posteriori. Comparaison menée **sur
> dossier**, sans déploiement d'essai chez les fournisseurs écartés. Les
> conséquences décrites sont constatées en exploitation réelle, dont un
> incident de renouvellement TLS encore ouvert à ce jour.

---

## Contexte

Auris manipule des **enregistrements audio de réunions professionnelles** et
leurs transcriptions. C'est le fait déterminant de cette décision.

Ces données sont personnelles au sens du RGPD, et peuvent être sensibles : une
réunion contient des propos identifiants sur des personnes qui ne sont pas
toutes utilisatrices du service. Le modèle de données en tient compte — la
table `consents` matérialise un consentement explicite au titre des articles 7
et 9, et la suppression est logique (`deleted_at`) pour honorer l'article 17
(voir `docs/architecture/schema_bdd_auris.md`).

Ce que l'hébergement doit fournir :

- une machine exposée sur Internet, avec nom de domaine et TLS ;
- un stockage objet pour les fichiers audio, que la base ne stocke jamais —
  seulement leur `storage_key` ;
- une base PostgreSQL (ADR-006) et ses sauvegardes ;
- de quoi faire tourner Keycloak (ADR-005) et un proxy inverse.

Deux contraintes de projet : **aucun budget d'entreprise** — c'est un projet
d'étudiants, financé sur leurs deniers — et un calendrier de l'ordre du
trimestre, déjà largement consommé par le métier.

---

## Options envisagées

### Option A — Amazon Web Services

L'offre la plus complète et la mieux documentée du marché. Une architecture
« dans les règles » aurait combiné ECS ou Fargate pour les conteneurs, RDS pour
PostgreSQL, S3 pour l'audio, CloudFront devant le front, le tout décrit en
Terraform.

Deux obstacles.

**Le premier est juridique.** AWS dispose bien d'une région à Paris
(`eu-west-3`), et les données y résident physiquement en France : sur ce point
précis, AWS et OVH sont équivalents, et prétendre le contraire serait faux.
La différence est ailleurs. Amazon est une société de droit américain, donc
susceptible d'être visée par le *CLOUD Act*, qui permet aux autorités des
États-Unis de réclamer des données détenues par une entreprise américaine
indépendamment du lieu de stockage. Depuis l'arrêt *Schrems II*, s'appuyer sur
un opérateur relevant de ce droit impose au responsable de traitement une
analyse et des garanties supplémentaires. Pour un service qui héberge des
enregistrements de réunions, nous avons préféré **ne pas avoir à mener ce
raisonnement** plutôt qu'à le documenter.

**Le second est financier.** La facturation est à l'usage, avec des frais de
sortie de données. Un projet étudiant sans plafond de dépenses y est exposé à
une facture imprévue — une boucle de traitement mal maîtrisée, un dépôt
répété de fichiers audio — sans mécanisme d'arrêt automatique.

**Écarté :** exposition au droit extraterritorial sur des données sensibles,
et facturation non bornée sur un projet sans budget.

### Option B — Google Cloud Platform

Le raisonnement est identique à celui d'AWS : société de droit américain, même
exposition juridique, même modèle de facturation à l'usage. L'offre technique
est comparable (Cloud Run, Cloud SQL, Cloud Storage).

**Écarté :** pour les mêmes motifs qu'AWS, sans avantage distinctif qui
justifierait de les accepter.

### Option C — OVHcloud

Opérateur français, données hébergées à Gravelines (région `gra`), soumis au
seul droit européen.

- **Un VPS à prix fixe mensuel**, qui héberge l'ensemble de la pile via Docker
  Compose : PostgreSQL, backend, frontend, Keycloak, nginx. Le coût est connu
  d'avance et ne peut pas déraper.
- **Un stockage objet compatible S3**
  (`https://s3.gra.io.cloud.ovh.net`), utilisable avec les outils standard.
- **Cohérence avec le reste de la pile** : le moteur de transcription retenu
  est lui aussi européen (ADR-004). L'ensemble des données d'Auris — audio,
  transcriptions, résumés, identités — reste sous droit européen, sans
  exception à justifier.

---

## Décision

**Nous retenons OVHcloud** : un VPS unique pour l'application, l'Object Storage
de Gravelines pour les fichiers audio et les sauvegardes.

Le motif décisif est la nature des données. Sur un service qui enregistre des
réunions, la question « où sont mes données, et qui peut légalement y
accéder ? » est la première que posera un utilisateur professionnel — et le
jury. Y répondre par « en France, chez un opérateur européen, sans exception »
est plus solide que d'exposer un montage de garanties contractuelles.

Le second motif est la maîtrise du coût : un prix fixe est une contrainte
saine sur un projet étudiant.

Cette décision est par ailleurs **peu coûteuse à annuler**, ce qui a pesé — voir
plus bas.

---

## Conséquences

### Positives

- **Aucun verrou technique.** Le stockage objet d'OVH parle le protocole S3, si
  bien que le projet utilise les outils d'Amazon pour s'adresser à OVH :
  `aiobotocore` dans `backend/app/services/storage_service.py`, et l'interface
  en ligne de commande `aws s3 cp` dans `infra/scripts/backup-postgres.sh`.
  Migrer vers AWS S3 se réduirait à changer une URL de point d'entrée et deux
  identifiants.
- **Coût mensuel fixe et connu**, sans frais de sortie.
- **Souveraineté cohérente sur toute la chaîne**, sans transfert hors UE à
  documenter.
- Une pile décrite entièrement en Docker Compose, donc reproductible ailleurs :
  la même commande relève le projet sur n'importe quelle machine Linux.

### Négatives

Elles se ramènent à un même principe : **rien n'est infogéré, donc tout est à
notre charge.**

- **La base de données est un conteneur que nous exploitons nous-mêmes.** Pas
  de sauvegarde automatique, pas de restauration à un instant donné, pas de
  bascule. Il a fallu écrire la chaîne complète :
  `infra/scripts/backup-postgres.sh` (dépôt d'un `pg_dump` chiffré sur
  l'Object Storage), `cleanup-old-backups.sh` (rétention de 30 jours),
  `restore-postgres.sh` et `test-backup-restore.sh`. RDS l'aurait fourni.
- **Un seul VPS, donc un seul point de défaillance.** Ni redondance, ni montée
  en charge automatique. Si la machine tombe, Auris est indisponible. C'est
  précisément ce qui a rendu nécessaire la surveillance des services et les
  alertes par courriel (SCRUM-176).
- **Le système d'exploitation, les mises à jour et TLS sont à notre charge — et
  cela a déjà produit un incident.** Le certificat Let's Encrypt a été
  enregistré en mode `standalone` ; or nginx occupe le port 80 en permanence,
  si bien que **le renouvellement automatique échouera à l'échéance du
  20 novembre 2026** s'il n'est pas basculé en mode `webroot` d'ici là. Un
  certificat infogéré n'aurait pas posé la question.
- **Moins d'outillage et de documentation** que chez les hyperscalers : les
  réponses aux problèmes rencontrés sont plus longues à trouver.

### Ce qu'il faudrait pour revenir en arrière

C'est la décision la plus réversible des sept, et c'est ce qui a permis de la
prendre sans longue délibération :

- **stockage** : changer `OVH_ENDPOINT_URL` et les identifiants, le code
  restant inchangé puisqu'il parle déjà S3 ;
- **application** : la pile est en Docker Compose, transposable sur n'importe
  quel hébergeur de conteneurs ;
- **base** : un `pg_dump` restauré ailleurs.

Le principal travail de migration porterait sur le DNS, TLS et la
configuration de Keycloak — de l'ordre de la journée, pas du chantier.

---

## Références

- Code : `backend/app/services/storage_service.py`,
  `infra/docker-compose.prod.yml`, `infra/scripts/backup-postgres.sh`,
  `infra/scripts/renew-ssl.sh`
- RGPD : `docs/architecture/schema_bdd_auris.md` (tables `consents`,
  suppression logique)
- Décisions liées : [ADR-004](ADR-004-voxtral.md) (moteur européen),
  [ADR-006](ADR-006-postgresql.md) (base exploitée en propre)
