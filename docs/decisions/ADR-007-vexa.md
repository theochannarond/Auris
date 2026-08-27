# ADR-007 — Vexa plutôt que Daily.co pour la captation des réunions vidéo

| | |
|---|---|
| **Statut** | Acceptée — intégrée, non opérationnelle en production à ce jour |
| **Date de la décision** | Juillet 2026 |
| **Date de rédaction** | 26 août 2026 |
| **Décideurs** | Enzo Bandinu, Théo Channarond, Mathis Fonbonne, Lydie Havugimana |
| **Périmètre** | `backend/app/services/vexa_service.py`, `backend/app/api/v1/webhooks.py` |

> **Note de méthode.** Document rédigé a posteriori. Comparaison menée **sur
> dossier**. Ce document décrit la décision la plus fragile des sept : la
> fonctionnalité est intégrée au code mais n'est pas active en production, et
> une vérification de conformité reste à mener (voir « Conséquences »).

---

## Contexte

Auris propose deux modes de captation :

- le **mode dictaphone**, pour une réunion en présentiel — le navigateur
  enregistre via `MediaRecorder` ;
- le **mode vidéo**, pour une réunion en visioconférence.

Le second pose une question que le premier ne pose pas : **la réunion n'a pas
lieu dans Auris.** Elle se tient sur Google Meet, Zoom ou Teams, parce que
c'est là que l'organisation de l'utilisateur travaille déjà. L'utilisateur
colle un lien de réunion (colonne `meeting_link`) et attend qu'Auris en produise
le compte rendu.

L'exigence de produit est donc précise : **capter l'audio d'une réunion qui se
tient ailleurs, sans rien changer aux habitudes des participants.** Demander à
une équipe de migrer sa visioconférence pour utiliser un assistant de compte
rendu reviendrait à condamner le produit.

S'ajoute une exigence légale : enregistrer une réunion sans que les
participants en soient informés n'est pas acceptable, ni juridiquement ni
déontologiquement — ce qui rejoint le dispositif de consentement décrit à
l'ADR-006.

---

## Options envisagées

### Option A — Daily.co

Daily.co est une infrastructure WebRTC : elle fournit les briques pour
**construire son propre produit de visioconférence** — salles, flux audio et
vidéo, enregistrement côté serveur.

C'est un excellent produit, mais **ce n'est pas un outil de la même nature**
que ce que le besoin appelle. Utiliser Daily.co supposerait qu'Auris héberge
lui-même les réunions : il faudrait développer une application de
visioconférence complète, puis convaincre les utilisateurs d'abandonner Meet,
Zoom ou Teams au profit d'Auris pour que le compte rendu soit possible.

Cela reviendrait à changer de produit. Auris cesserait d'être un assistant qui
se greffe sur l'existant pour devenir une plateforme de réunion concurrente de
Google et de Microsoft — un projet sans rapport avec le calendrier et les
moyens de l'équipe.

**Écarté :** répond à un autre besoin. La comparaison avec Vexa n'oppose pas
deux solutions au même problème, mais deux problèmes différents.

### Option B — Capter l'audio depuis le poste de l'utilisateur

Enregistrer localement le son de l'onglet ou du système pendant la réunion,
en réutilisant la chaîne du mode dictaphone.

C'est la solution la moins coûteuse, et elle ne dépend d'aucun tiers. Mais elle
est fragile : la capture du son d'un onglet est inégalement prise en charge
selon les navigateurs et les systèmes, elle impose à l'utilisateur de laisser
sa machine allumée et l'onglet ouvert pendant toute la réunion, et elle
n'enregistre que ce que son propre poste reçoit. Surtout, elle est **invisible
pour les autres participants**, qui ne sont jamais informés de
l'enregistrement.

**Écarté :** trop fragile en exploitation, et discutable sur le plan de
l'information des participants.

### Option C — Vexa

Vexa envoie un **bot participant** dans la réunion existante. Le bot rejoint
Meet, Zoom ou Teams comme un invité, capte l'audio, et signale son activité par
webhook.

- **Aucun changement d'habitude.** L'utilisateur continue de réunir son équipe
  là où il le fait déjà ; il colle simplement le lien dans Auris.
- **Le bot est visible.** Il apparaît dans la liste des participants sous le
  nom « Auris Assistant » (`vexa_service.py`). L'enregistrement est donc
  annoncé par construction, à tous les participants, y compris ceux qui ne
  sont pas utilisateurs d'Auris.
- **Plusieurs plateformes couvertes** par une seule intégration.
- **Un cycle de vie signalé par événements**, ce qui s'accorde avec le
  traitement asynchrone retenu à l'ADR-001.

---

## Décision

**Nous retenons Vexa**, appelé par `spawn_bot()` au lancement d'une réunion
vidéo, et renvoyant ses événements sur `POST /api/v1/webhooks/vexa`.

Le motif est le respect de l'existant : un assistant de réunion doit s'adapter
aux outils de ses utilisateurs, pas l'inverse. Vexa est la seule des trois
options qui le permette.

La visibilité du bot dans la liste des participants a pesé de façon
indépendante : elle transforme une contrainte technique en garantie de
transparence.

Le webhook est établi comme **seule source de vérité du statut** d'une réunion
— règle inscrite dans `docs/architecture/schema_bdd_auris.md` : le statut n'est
jamais modifié au lancement du bot, uniquement à réception d'un événement. Le
gestionnaire est idempotent et ne fait jamais reculer un statut.

---

## Conséquences

### Positives

- Le produit fonctionne avec Meet, Zoom et Teams sans intégration spécifique à
  chacun.
- L'enregistrement est annoncé aux participants par la présence du bot.
- L'automate d'états est robuste : `bot.joined`, `bot.left` et `bot.failed` ne
  sont pris en compte que depuis un statut cohérent, ce qui rend les
  redistributions d'événements sans effet
  (`backend/app/api/v1/webhooks.py`).
- Le mode dictaphone reste disponible : une défaillance du mode vidéo ne prive
  pas les utilisateurs du produit.

### Négatives

C'est la décision qui expose le plus, et plusieurs points sont encore ouverts.

- **La fonctionnalité n'est pas active en production.** `VEXA_API_KEY` et
  `VEXA_WEBHOOK_SECRET` ne sont pas renseignées sur le serveur : le mode vidéo
  est intégré au code mais ne fonctionne pas aujourd'hui sur
  `https://aurishetic.fr`. À vérifier avant toute démonstration.
- **La conformité de souveraineté n'a pas été vérifiée pour ce prestataire.**
  Les ADR-003 et ADR-004 écartent explicitement les fournisseurs relevant du
  droit américain pour l'hébergement et la transcription. Or l'audio des
  réunions transite ici par Vexa, dont le régime juridique et le lieu
  d'hébergement n'ont pas été examinés au moment du choix. **C'est une lacune
  dans la cohérence de la démarche**, et elle doit être levée : soit la
  vérification confirme la compatibilité, soit ce choix doit être réexaminé.
- **Un échec de lancement du bot est silencieux.** `spawn_bot()` intercepte
  toute exception, l'affiche avec `print()` et renvoie un dictionnaire
  d'erreur ; la création de la réunion se poursuit normalement. L'utilisateur
  obtient donc une réunion en attente dont le bot n'a jamais été lancé, sans
  message. Le commentaire du code assume ce choix — ne pas bloquer la création
  — mais il manque une remontée à l'utilisateur. Accessoirement, `print()`
  contourne la journalisation structurée mise en place par ailleurs.
- **L'authentification du webhook est sommaire.** `verify_vexa_secret()`
  compare un secret partagé transmis en en-tête, avec un opérateur `!=` dont le
  temps d'exécution dépend du contenu. Ce n'est pas une signature HMAC du
  corps de la requête, et la docstring reconnaît elle-même qu'il s'agit d'une
  mesure « en attendant confirmation du mécanisme Vexa ». Cette confirmation
  reste à obtenir.
- **Dépendance forte à un prestataire jeune.** Tout le mode vidéo repose sur
  lui, et les bots de réunion sont par nature exposés aux évolutions des
  plateformes hôtes : un changement chez Google ou Microsoft peut interrompre
  le service sans préavis.
- **Le bot doit parfois être admis** par l'organisateur, selon les réglages de
  la réunion. La captation n'est donc pas garantie sans action humaine.

### Ce qu'il faudrait pour revenir en arrière

L'intégration est confinée à deux fichiers : `vexa_service.py` pour le
lancement du bot, `webhooks.py` pour la réception des événements. Le reste du
système ne connaît que le statut de la réunion et le fichier audio produit.

Changer de prestataire de bot reviendrait à réécrire ces deux fichiers en
conservant le même contrat d'événements. En dernier recours, le mode
dictaphone couvre déjà le besoin de base sans aucune dépendance externe.

---

## Références

- Code : `backend/app/services/vexa_service.py`,
  `backend/app/api/v1/webhooks.py`, `backend/app/schemas/webhook.py`,
  `frontend/src/components/ui/BotStatusNotification.tsx`
- Règle d'équipe : `docs/architecture/schema_bdd_auris.md` (le webhook est la
  seule source de vérité du statut)
- Décisions liées : [ADR-003](ADR-003-ovh.md) et
  [ADR-004](ADR-004-voxtral.md) (ligne de souveraineté à confronter à ce
  choix), [ADR-001](ADR-001-fastapi.md) (traitement par événements)
