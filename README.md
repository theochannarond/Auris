
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


## Démarrage rapide

```bash
# Cloner le repo
git clone https://github.com/theochannarond/Auris.git
cd Auris

# Configurer les variables d'environnement
copy .env.example .env
# Remplir .env avec vos vraies clés

# Lancer tous les services
docker-compose up
```

## Gouvernance

- **Branches** : `type/SCRUM-USXX-description`
- **Commits** : `type(scope) : description [SCRUM-XX]`
- **Tickets** : Jira — projet Auris
