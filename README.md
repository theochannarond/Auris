
# Auris

![CI](https://github.com/theochannarond/Auris/actions/workflows/ci.yml/badge.svg)

Assistant de réunion intelligent — stack européenne souveraine, conforme RGPD.

## Stack technique

| Couche           | Technologie                       |
| ---------------- | --------------------------------- |
| Frontend         | React + TypeScript + Vite         |
| Backend          | FastAPI (Python)                  |
| Base de données | PostgreSQL + SQLAlchemy + Alembic |
| Authentification | Keycloak                          |
| Transcription    | Voxtral Mini V2 (Mistral AI)      |
| Résumé         | Mistral Small 4 (Mistral AI)      |
| Capture audio    | Vexa (auto-hébergé OVH)         |
| Infra            | Docker + Docker Compose           |
| Hébergement     | OVH SecNumCloud                   |

## Prérequis

Tout le projet tourne dans des conteneurs. **Docker et Git suffisent** pour lancer Auris — Python et Node ne sont nécessaires que pour travailler hors conteneur.

### Indispensables

| Outil | Version minimale | Vérification |
| ----- | ---------------- | ------------ |
| Docker Engine | 24.0 | `docker --version` |
| Docker Compose | v2.20 | `docker compose version` |
| Git | 2.30 | `git --version` |

Sous Windows et macOS, **Docker Desktop** fournit les deux premiers d'un coup. Sous Linux, installez Docker Engine puis le greffon `docker-compose-plugin`.

Attention à la syntaxe : ce projet utilise `docker compose` (Compose v2, en deux mots) et non `docker-compose` (v1, obsolète depuis 2023). Les deux ne se comportent pas de la même façon.

### Pour travailler hors conteneur

Nécessaires seulement si vous lancez les tests ou les serveurs de développement directement sur votre machine, sans passer par Docker.

| Outil | Version | Pourquoi cette version |
| ----- | ------- | ---------------------- |
| Python | 3.12 | version de `backend/Dockerfile` et du job `backend` de la CI |
| Node.js | 22 LTS | version de `frontend/Dockerfile` et des jobs `frontend` et `e2e` de la CI |

Ne prenez pas une version supérieure « pour être tranquille » : si vos tests passent en local sur une autre version que celle de la CI, ils peuvent échouer une fois poussés — et l'inverse est encore plus désagréable.

### Ressources machine

- **8 Go de RAM** au minimum. Les quatre conteneurs cohabitent, et Keycloak à lui seul demande environ 1 Go.
- **5 Go d'espace disque** pour les images et le volume PostgreSQL.

## Installation

Comptez une dizaine de minutes au premier lancement, dont l'essentiel en téléchargement d'images.

### 1. Cloner le dépôt

```bash
git clone https://github.com/theochannarond/Auris.git
cd Auris
```

### 2. Créer le fichier d'environnement

**Le fichier va dans `infra/`, pas à la racine du dépôt.** C'est le piège le plus coûteux du projet : Docker Compose cherche son `.env` dans le dossier du fichier de composition, donc un `.env` placé à la racine est purement et simplement ignoré. La pile démarre quand même, avec toutes les variables vides, et échoue plus tard de façon incompréhensible.

```bash
cp .env.example infra/.env          # macOS / Linux
```

```powershell
Copy-Item .env.example infra\.env   # Windows PowerShell
```

Les valeurs d'exemple suffisent pour un premier démarrage. Deux d'entre elles devront être renseignées ensuite : `KEYCLOAK_CLIENT_SECRET` à l'étape 4, et `MISTRAL_API_KEY` le jour où vous voudrez transcrire. Le détail de chaque variable est dans la [section dédiée](#variables-denvironnement).

### 3. Lancer la pile

```bash
docker compose -f infra/docker-compose.yml up
```

Le premier lancement construit les images et télécharge PostgreSQL, Keycloak et Node : **3 à 5 minutes** selon votre connexion. Gardez ce terminal ouvert, les journaux des quatre services s'y affichent. La [sortie attendue](#procédure-docker-compose-up) est documentée plus bas.

**Keycloak met environ une minute de plus que les autres à répondre.** Tant qu'il n'a pas affiché `started in`, `localhost:8080` refuse la connexion — ce n'est pas une panne.

### 4. Importer le realm Keycloak et récupérer le secret client

L'authentification ne fonctionnera pas tant que le realm `auris` n'existe pas. La procédure complète est décrite dans la [section Keycloak](#import-du-realm-keycloak). En résumé : importer `infra/keycloak-realm.json`, copier le secret du client `auris-backend`, le coller dans `infra/.env`, puis relancer le backend :

```bash
docker compose -f infra/docker-compose.yml restart backend
```

### 5. Créer un utilisateur de test

L'export du realm ne contient **aucun utilisateur** — il faut en créer un pour pouvoir se connecter. La marche à suivre est dans la même section Keycloak.

### 6. Vérifier que tout répond

| Service | URL | Attendu |
| ------- | --- | ------- |
| Frontend | http://localhost:5173 | page de connexion Auris |
| API — documentation | http://localhost:8000/docs | interface Swagger |
| API — santé | http://localhost:8000/health | `{"status":"ok",...}` |
| Keycloak | http://localhost:8080 | console d'administration |
| PostgreSQL | `localhost:5432` | accessible via un client SQL |

### Les fois suivantes

```bash
docker compose -f infra/docker-compose.yml up -d       # en arrière-plan
docker compose -f infra/docker-compose.yml logs -f     # suivre les journaux
docker compose -f infra/docker-compose.yml down        # arrêter
```

Les images étant déjà construites et le volume PostgreSQL conservé, le démarrage tombe à une quinzaine de secondes — Keycloak mis à part.

Le code du backend et du frontend est monté depuis votre disque : **vos modifications sont prises en compte sans reconstruire l'image**, uvicorn et Vite rechargent tout seuls. Une reconstruction n'est nécessaire qu'après une modification de `requirements.txt` ou de `package.json` :

```bash
docker compose -f infra/docker-compose.yml up --build
```

## Variables d'environnement

Toute la configuration passe par un seul fichier, **`infra/.env`**, créé à partir de `.env.example`. Il n'est jamais versionné : `.gitignore` exclut `.env` et `.env.*`, à l'exception des modèles `*.example`.

### Ce qui est nécessaire pour démarrer en local

| Variable | Valeur locale | Rôle |
| -------- | ------------- | ---- |
| `POSTGRES_USER` | `auris` | identifiant PostgreSQL, créé au premier démarrage |
| `POSTGRES_PASSWORD` | libre | mot de passe PostgreSQL |
| `KEYCLOAK_ADMIN` | `admin` | compte d'administration de la console Keycloak |
| `KEYCLOAK_ADMIN_PASSWORD` | libre | mot de passe de ce compte |
| `KEYCLOAK_URL` | `http://keycloak:8080` | **nom du service Docker**, pas `localhost` |
| `KEYCLOAK_REALM` | `auris` | doit correspondre au realm importé |
| `KEYCLOAK_CLIENT_ID` | `auris-backend` | client confidentiel utilisé par l'API |
| `KEYCLOAK_CLIENT_SECRET` | *à récupérer* | généré à l'import du realm, voir la section Keycloak |

### Ce qui peut rester vide au début

Ces variables ne bloquent pas le démarrage. Elles ne servent qu'aux fonctionnalités correspondantes, qui échoueront proprement tant qu'elles ne sont pas renseignées.

| Variable | Sans elle |
| -------- | --------- |
| `MISTRAL_API_KEY` | pas de transcription ni de résumé |
| `OVH_ACCESS_KEY`, `OVH_SECRET_KEY`, `OVH_BUCKET_NAME` | l'audio bascule sur le stockage local de repli |
| `VEXA_API_KEY`, `VEXA_WEBHOOK_SECRET` | pas de capture de réunion visio |

### Trois pièges à connaître

**`KEYCLOAK_URL` prend le nom du service Docker, pas `localhost`.** C'est le backend qui appelle cette URL, depuis l'intérieur du réseau Docker, où `localhost` désigne son propre conteneur. `http://localhost:8080` n'est correct que si vous lancez le backend directement sur votre machine.

**`DATABASE_URL` est ignorée par Docker Compose.** Le fichier de composition reconstruit lui-même l'URL à partir de `POSTGRES_USER` et `POSTGRES_PASSWORD`. Modifier `DATABASE_URL` en espérant changer la base à laquelle se connecte le conteneur n'a aucun effet — elle ne sert que si vous lancez le backend hors conteneur, ou pour les migrations Alembic.

**Les variables `VITE_*` ne servent pas en développement local.** Le compose ne les transmet pas au conteneur frontend, qui retombe sur ses valeurs par défaut — lesquelles conviennent en local. Elles ne comptent qu'à la **construction** de l'image de production, où Vite les écrit en dur dans le bundle. Les définir au démarrage d'un conteneur de production n'aurait aucun effet.

### Le second modèle, `backend/.env.example`

Il existe un deuxième fichier d'exemple, destiné à ceux qui lancent le backend **hors conteneur** (`uvicorn` directement sur la machine). Il contient quelques variables absentes du modèle racine — `OVH_ENDPOINT_URL`, `OVH_REGION`, `OVH_BACKUP_BUCKET` — qui ont des valeurs par défaut dans le code et que le compose de développement ne transmet pas.

Pour une installation normale via Docker, **ignorez-le** : seul `infra/.env` est lu.

## Structure du projet



auris/

├── frontend/             # React + TypeScript + Vite

│   └── src/

│       ├── assets/       # Images, icônes, fonts

│       ├── components/   # Composants réutilisables

│       ├── pages/        # Une page = une route

│       ├── services/     # Appels API vers le backend

│       ├── hooks/        # Custom React hooks

│       ├── store/        # État global

│       ├── types/        # Interfaces TypeScript

│       └── utils/        # Fonctions utilitaires

├── backend/              # FastAPI + Python

│   ├── app/

│   │   ├── api/v1/       # Endpoints REST

│   │   ├── core/         # Configuration centrale

│   │   ├── models/       # SQLAlchemy (tables)

│   │   ├── schemas/      # Pydantic (API I/O)

│   │   └── services/     # Logique métier

│   └── tests/

├── infra/                # Docker Compose

└── docs/                 # Documentation technique


## Gouvernance

- **Branches** : `type/SCRUM-USXX-description`
- **Commits** : `type(scope) : description [SCRUM-XX]`
- **Tickets** : Jira — projet Auris
