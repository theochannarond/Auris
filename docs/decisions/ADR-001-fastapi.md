# ADR-001 — FastAPI plutôt que Django ou Flask

| | |
|---|---|
| **Statut** | Acceptée — en production |
| **Date de la décision** | Juillet 2026, au démarrage du projet |
| **Date de rédaction** | 26 août 2026 |
| **Décideurs** | Enzo Bandinu, Théo Channarond, Mathis Fonbonne, Lydie Havugimana |
| **Périmètre** | `backend/` |

> **Note de méthode.** Ce document est rédigé a posteriori : la décision a été
> prise au démarrage du projet et le code est en production depuis. Les options
> ci-dessous ont été comparées **sur dossier**, sans prototype de chacune. Les
> conséquences, en revanche, ne sont pas théoriques — elles sont constatées dans
> le code existant, et l'une d'elles est un défaut assumé (voir plus bas).

---

## Contexte

Le backend d'Auris reçoit un enregistrement audio (dictaphone) ou un lien de
réunion vidéo, puis pilote une chaîne de traitement jusqu'au compte rendu.

Son travail n'est presque jamais du calcul. C'est de **l'attente réseau**.
Un cycle complet enchaîne quatre échanges avec des services externes :

1. dépôt de l'audio sur OVH Object Storage (ADR-003) ;
2. transcription par Voxtral (ADR-004) — le délai d'attente configuré est de
   **300 secondes** (`VOXTRAL_TIMEOUT_SEC`, `backend/app/core/database.py`) ;
3. résumé par Mistral Small (`mistral_service.py`) ;
4. réception des webhooks Vexa signalant l'état du bot (ADR-007).

Cette durée est le fait structurant de tout le backend. Une transcription
d'une réunion d'une heure mobilise la requête plusieurs minutes.

Trois autres contraintes cadrent le choix :

- **Aucune page HTML n'est rendue côté serveur.** Le front est une application
  React autonome (ADR-002) ; le backend ne produit que du JSON.
- **L'authentification est déléguée à Keycloak** (ADR-005). Le backend ne gère
  ni inscription, ni mot de passe, ni session : il se contente de valider une
  signature RS256 (`backend/app/core/security.py`).
- **Le front et l'API sont développés en parallèle par des personnes
  différentes.** Le contrat d'interface doit rester lisible et à jour sans
  qu'on ait à l'écrire à la main.

---

## Options envisagées

### Option A — Django + Django REST Framework

Le framework Python le plus établi, et le plus complet : ORM, migrations,
interface d'administration, système d'utilisateurs, moteur de gabarits.

Le problème n'est pas Django, c'est qu'Auris n'a besoin d'aucune de ces
briques. Le moteur de gabarits ne sert à rien face à une SPA. Le système
d'utilisateurs fait doublon avec Keycloak. L'interface d'administration n'a
pas d'usage identifié. Restent l'ORM et les migrations — que SQLAlchemy et
Alembic fournissent aussi, sans le reste.

Surtout, Django reste au fond un framework **synchrone** (WSGI). Le support
ASGI existe mais l'ORM et une grande partie de l'écosystème ne sont pas
pleinement asynchrones. Avec des travailleurs synchrones, chaque transcription
en cours occupe un travailleur entier pendant cinq minutes : dix
transcriptions simultanées demandent dix travailleurs, dont l'essentiel du
temps est passé à ne rien faire d'autre qu'attendre le réseau.

**Écarté :** on paierait la complexité d'un framework complet pour n'en
utiliser qu'un quart, avec un modèle d'exécution mal adapté à des appels
externes de plusieurs minutes.

### Option B — Flask

L'inverse : minimal, rapide à prendre en main, aucune brique imposée.

Mais tout ce dont Auris a besoin est alors à assembler à la main. La
validation des entrées et des sorties (une bibliothèque tierce), la
documentation d'API (une autre), l'injection de dépendances pour la session
de base de données et l'utilisateur courant (à écrire soi-même). Sur un projet
à quatre mains, chacune de ces briques est une convention de plus à faire
respecter par tout le monde.

Flask sait exécuter des vues `async` depuis la version 2, mais il reste bâti
sur WSGI : chaque requête asynchrone est exécutée dans une boucle
d'événements propre, sur un travailleur synchrone. On y perd le bénéfice
principal, qui est de partager une même boucle entre des centaines d'attentes
réseau.

**Écarté :** pour arriver à l'équivalent de FastAPI il aurait fallu
rassembler quatre bibliothèques et écrire la colle — sans obtenir le modèle
asynchrone recherché.

### Option C — FastAPI

Bâti sur ASGI (Starlette) et sur Pydantic.

- **Asynchrone de bout en bout.** Une requête qui attend Voxtral rend la main
  à la boucle d'événements ; un seul processus traite plusieurs transcriptions
  simultanées. Toute la chaîne d'appels sortants suit ce modèle :
  `httpx.AsyncClient` pour Voxtral, Mistral et Vexa, `aiobotocore` pour OVH.
- **Validation par les types.** Les schémas de `backend/app/schemas/` sont des
  modèles Pydantic ; la validation des entrées, la sérialisation des sorties
  et la documentation découlent des mêmes annotations, écrites une fois.
- **Documentation OpenAPI générée.** L'interface `/docs` est toujours à jour
  puisqu'elle est dérivée du code. C'est le contrat que consomme le front.
- **`BackgroundTasks` intégré.** La route de transcription répond
  immédiatement `202 Accepted` et poursuit le traitement en arrière-plan
  (`backend/app/api/v1/transcriptions.py`) — sans ajouter de file de messages.
- **Injection de dépendances native.** `Depends(get_current_user)` suffit à
  protéger une route.

---

## Décision

**Nous retenons FastAPI** (`fastapi==0.111.0`, servi par Uvicorn), avec
SQLAlchemy 2 et Alembic pour la persistance.

La raison décisive est le délai de Voxtral. Un backend dont le métier consiste
à attendre des services externes pendant des minutes doit être asynchrone :
c'est ce qui permet de tenir plusieurs traitements simultanés sur un seul VPS
mutualisé (ADR-003). Les autres avantages — validation, documentation générée
— ont pesé, mais ils auraient pu être obtenus autrement. Le modèle
d'exécution, non.

À l'inverse, ce que Django apporte en propre — administration, utilisateurs,
gabarits — correspond exactement à ce qu'Auris délègue ailleurs ou n'utilise
pas.

---

## Conséquences

### Positives

- Un seul processus Uvicorn absorbe plusieurs transcriptions simultanées, ce
  qui compte sur un VPS unique hébergeant aussi la base, Keycloak et nginx.
- Le contrat d'API est généré, donc jamais désynchronisé du code.
- Les mêmes annotations de types servent à la validation, à la sérialisation
  et à la documentation.
- La réponse `202 Accepted` avec traitement en arrière-plan a évité d'ajouter
  Celery et Redis à l'infrastructure.

### Négatives

- **Aucune brique fournie.** Migrations (Alembic), authentification
  (Keycloak), structure du projet : tout est à mettre en place et à tenir.
- **L'accès base de données est resté synchrone.** Le projet utilise
  `psycopg2-binary` et la couche synchrone de SQLAlchemy, pas `asyncpg`. Une
  requête SQL bloque donc la boucle d'événements pendant son exécution. C'est
  visible dans `backend/app/main.py` : `health_check` est déclarée `async`
  mais appelle `check_db_connection()` de façon bloquante. Les requêtes sont
  courtes et le défaut est sans effet mesurable aujourd'hui, mais il est réel
  et il contredit en partie la justification du choix. Le corriger suppose de
  passer à `asyncpg` et à la session asynchrone de SQLAlchemy.
- **`BackgroundTasks` ne survit pas au redémarrage du conteneur.** Une
  transcription en cours pendant un déploiement est perdue. Le mécanisme de
  reprise (`retry_count`, route de relance) compense, mais une vraie file de
  messages serait nécessaire pour garantir le traitement.
- Écosystème plus jeune que celui de Django : moins d'extensions prêtes à
  l'emploi, davantage de code à écrire pour les besoins non standards.

### Ce qu'il faudrait pour revenir en arrière

Un changement de framework toucherait `backend/app/api/`, `backend/app/main.py`
et l'ensemble des schémas Pydantic. Les modèles SQLAlchemy, les services
(`voxtral_service`, `mistral_service`, `storage_service`, `vexa_service`) et
les migrations Alembic sont indépendants du framework web et survivraient.
Le coût serait significatif mais circonscrit à la couche HTTP.

---

## Références

- Code : `backend/app/main.py`, `backend/app/api/v1/`, `backend/app/schemas/`
- Dépendances : `backend/requirements.txt`
- Décisions liées : [ADR-002](ADR-002-react.md) (SPA React),
  [ADR-005](ADR-005-keycloak.md) (authentification déléguée),
  [ADR-006](ADR-006-postgresql.md) (persistance)
