# ADR-006 — PostgreSQL plutôt que MongoDB

| | |
|---|---|
| **Statut** | Acceptée — en production |
| **Date de la décision** | Juillet 2026 |
| **Date de rédaction** | 26 août 2026 |
| **Décideurs** | Enzo Bandinu, Théo Channarond, Mathis Fonbonne, Lydie Havugimana |
| **Périmètre** | `backend/app/models/`, `backend/alembic/`, service `db` |

> **Note de méthode.** Document rédigé a posteriori. Comparaison menée **sur
> dossier**. Les conséquences sont constatées dans le code, dont un écart de
> fidélité entre l'environnement de test et la production.

---

## Contexte

Le modèle de données d'Auris est décrit dans
`docs/architecture/schema_bdd_auris.md`, document de référence de l'équipe.
Sa structure est une **chaîne stricte** :

```
users
├── consents        (1 utilisateur → N consentements)
└── meetings        (1 utilisateur → N réunions)
    └── audio_files     (1 réunion → 1 fichier audio)
        └── transcriptions  (1 fichier → 1 transcription)
            └── summaries       (1 transcription → 1 résumé)
```

Trois exigences pèsent sur le choix du moteur.

**L'effacement doit être total et garanti.** Une demande d'effacement au titre
de l'article 17 du RGPD porte sur l'utilisateur *et* sur tout ce qui lui est
rattaché : réunions, audio, transcriptions, résumés, consentements. Rien ne
doit survivre par oubli.

**Les transitions d'état doivent être fiables.** Une réunion suit le cycle
`pending → recording → processing → completed | failed`, piloté en partie par
un service externe (ADR-007). Une écriture partielle laisserait une réunion
dans un état incohérent.

**Le schéma est un contrat d'équipe.** Quatre personnes créent des modèles en
parallèle, à partir d'un document commun que chacun doit respecter — son
en-tête précise qu'il est « à lire AVANT de créer ou modifier un modèle ».

S'ajoute une donnée réellement peu structurée : les segments de diarisation et
les éléments extraits par le résumé — décisions, actions par responsable —
dont la forme n'est pas fixée à l'avance.

---

## Options envisagées

### Option A — MongoDB

Base orientée documents, sans schéma imposé.

Ses atouts sont réels sur d'autres projets : itération rapide quand la forme
des données n'est pas stabilisée, imbrication naturelle des structures,
partitionnement horizontal simple.

Aucun ne correspond à Auris.

La forme des données est stabilisée dès la conception, et documentée. Surtout,
**les garanties dont nous avons besoin devraient être réimplémentées dans le
code applicatif** : l'intégrité référentielle n'existe pas, donc la
propagation d'un effacement est à écrire à la main, dans chaque chemin de
suppression. Un seul chemin oublié laisse des données personnelles orphelines
en base — c'est-à-dire un manquement au RGPD, provoqué par un défaut que rien
ne signale.

Les transactions multi-documents existent depuis la version 4.0, mais
supposent un jeu de réplicas et ne sont pas la voie idiomatique.

Quant à l'absence de schéma, elle serait ici un inconvénient : à quatre, c'est
la garantie que les documents divergeront silencieusement.

**Écarté :** le modèle est relationnel, et les garanties d'intégrité seraient à
réécrire, sur le sujet où une erreur est la plus coûteuse juridiquement.

### Option B — PostgreSQL

Base relationnelle, et accessoirement très bonne base documentaire.

- **L'intégrité référentielle est assurée par le moteur.** Les clés étrangères
  portent `ON DELETE CASCADE` — visible dans `models/summary.py`,
  `models/transcription.py` — ou `ON DELETE SET NULL` là où le lien est
  optionnel. La suppression en cascade est une propriété de la base, pas une
  intention du code.
- **Transactions ACID par défaut**, sans configuration particulière.
- **Le schéma est explicite et versionné**, avec six migrations Alembic à ce
  jour. Toute évolution est tracée et rejouable à l'identique sur chaque
  environnement.
- **Type UUID natif**, conforme à la règle d'équipe « UUID partout, jamais
  d'entiers auto-incrémentés » — un identifiant de réunion n'est pas devinable
  et ne divulgue pas le volume d'activité du service.
- **JSONB pour ce qui est réellement libre.** Les colonnes `diarization`,
  `decisions` et `action_items` stockent des documents, indexables et
  interrogeables. La souplesse documentaire est donc obtenue **sans renoncer**
  aux garanties relationnelles sur le reste.

---

## Décision

**Nous retenons PostgreSQL 16**, avec SQLAlchemy 2 et Alembic pour les
migrations.

L'argument décisif est l'effacement RGPD. Confier la propagation d'une
suppression au moteur plutôt qu'au code applicatif transforme une obligation
juridique en une propriété structurelle : si la contrainte existe, elle
s'applique, y compris sur un chemin de suppression écrit plus tard par
quelqu'un d'autre. C'est exactement la garantie qu'on veut sur des
enregistrements de réunions.

Le second argument est que PostgreSQL n'imposait aucun renoncement : le seul
avantage de MongoDB qui nous concernait — le stockage de documents libres —
est couvert par JSONB.

À noter : le projet pratique aussi la **suppression logique** (`deleted_at`),
et la règle d'équipe est de ne jamais supprimer physiquement. La cascade est
donc un filet de sécurité pour l'effacement définitif, pas le mécanisme
quotidien.

---

## Conséquences

### Positives

- L'effacement complet d'un utilisateur est garanti par le moteur.
- Les jointures de la chaîne réunion → audio → transcription → résumé sont
  directes, sans agrégation applicative.
- Le schéma versionné sert de contrat entre les quatre développeurs ; une
  divergence de modèle apparaît à la migration, pas en production.
- JSONB couvre les besoins documentaires sans base supplémentaire.
- PostgreSQL s'auto-héberge sans difficulté en conteneur, conformément à
  l'ADR-003.

### Négatives

- **Les tests ne s'exécutent pas sur le même moteur que la production.**
  `backend/tests/conftest.py` utilise SQLite (`sqlite:///./test.db`). C'est
  rapide et sans dépendance, mais cela a un coût de fidélité : SQLite ne
  connaît pas JSONB, d'où le contournement de `models/types.py`
  (`JSONB().with_variant(JSON(), "sqlite")`), et ne vérifie pas les clés
  étrangères de la même manière. **Une suite de tests verte ne prouve donc pas
  que les cascades fonctionnent.** Or ces cascades sont précisément la
  justification principale du choix. Le corriger suppose de faire tourner un
  PostgreSQL de test dans l'intégration continue.
- **JSONB n'offre aucune garantie de forme.** Le contenu de `diarization`,
  `decisions` et `action_items` n'est validé par rien. Cette absence de filet
  est visible : la colonne `diarization` n'est jamais alimentée et rien ne le
  signale (voir ADR-004).
- **Chaque évolution de modèle exige une migration.** C'est une discipline —
  une migration oubliée casse le déploiement, une migration mal écrite est
  difficile à défaire une fois appliquée en production.
- **Le schéma freine l'itération précoce.** Ajouter un champ en cours de sprint
  coûte un aller-retour par Alembic, là où MongoDB n'aurait rien demandé.
- **La base est exploitée par nos soins**, avec les conséquences décrites à
  l'ADR-003 : sauvegardes, restauration et montées de version sont à notre
  charge.
- **La montée en charge horizontale** serait plus délicate qu'avec un
  partitionnement MongoDB. Ce n'est pas une contrainte aujourd'hui : le service
  tourne sur un VPS unique et le volume de réunions est sans commune mesure
  avec ce qui rendrait la question pertinente.

### Ce qu'il faudrait pour revenir en arrière

Un changement de moteur relationnel — vers MySQL ou MariaDB — resterait
modéré : SQLAlchemy abstrait l'essentiel, mais il faudrait remplacer les types
spécifiques à PostgreSQL (`UUID`, `JSONB`) et rejouer les migrations.

Un passage à MongoDB serait en revanche une refonte : disparition des clés
étrangères, réécriture applicative des cascades d'effacement, abandon
d'Alembic, et reprise de toutes les requêtes.

---

## Références

- Schéma de référence : `docs/architecture/schema_bdd_auris.md`
- Code : `backend/app/models/`, `backend/app/models/types.py`,
  `backend/alembic/versions/`, `backend/tests/conftest.py`
- Décisions liées : [ADR-003](ADR-003-ovh.md) (base auto-hébergée),
  [ADR-001](ADR-001-fastapi.md) (accès resté synchrone),
  [ADR-004](ADR-004-voxtral.md) (colonne `diarization` inexploitée)
