# Décisions d'architecture (ADR)

Ce dossier recense les **décisions techniques structurantes** du projet Auris :
ce qui a été choisi, ce qui a été écarté, pourquoi, et ce que le choix a coûté.

Un *Architecture Decision Record* n'est pas une documentation technique. Il ne
dit pas comment le code fonctionne — le README de la racine et
`docs/architecture/` s'en chargent. Il dit **pourquoi il est ainsi plutôt
qu'autrement**, de façon à ce qu'une personne arrivant sur le projet, ou y
revenant dans un an, n'ait pas à redécouvrir un raisonnement déjà mené.

---

## Les sept décisions

| # | Décision | Écarté | Motif décisif |
|---|---|---|---|
| [001](ADR-001-fastapi.md) | **FastAPI** | Django, Flask | Le backend attend des services externes jusqu'à 5 minutes : il lui faut un modèle asynchrone |
| [002](ADR-002-react.md) | **React** | Angular | Sur un projet court, le budget d'apprentissage devait aller au métier, pas au framework |
| [003](ADR-003-ovh.md) | **OVHcloud** | AWS, Google Cloud | Ne pas soumettre des enregistrements de réunions à un opérateur de droit américain |
| [004](ADR-004-voxtral.md) | **Voxtral (Mistral AI)** | AssemblyAI, Deepgram | Cohérence de souveraineté sur la donnée la plus sensible : le contenu des réunions |
| [005](ADR-005-keycloak.md) | **Keycloak** | Authentification maison, Auth0 | L'authentification est là où une erreur coûte le plus cher et où nous serions le moins compétents |
| [006](ADR-006-postgresql.md) | **PostgreSQL** | MongoDB | L'effacement RGPD doit être garanti par le moteur, pas par le code applicatif |
| [007](ADR-007-vexa.md) | **Vexa** | Daily.co, captation locale | Un assistant se greffe sur les outils de ses utilisateurs ; il ne leur en impose pas d'autres |

---

## Le fil conducteur

Trois de ces décisions — l'hébergement (003), la transcription (004) et
l'authentification (005) — répondent à la même question : **où vont les données
d'une réunion, et qui peut légalement y accéder ?**

Auris enregistre des propos tenus par des personnes qui ne sont pas toutes
utilisatrices du service. Cette donnée commande la ligne suivie : hébergement
en France, moteur de transcription européen, serveur d'identité auto-hébergé,
et effacement garanti par la base (006).

L'ADR-007 signale que cette ligne comporte **une lacune assumée** : le régime
juridique du prestataire de captation vidéo n'a pas été vérifié. Elle est
documentée là plutôt que passée sous silence.

---

## Note de méthode

Ces documents ont été **rédigés a posteriori**, en août 2026, alors que les
décisions dataient du démarrage du projet et que le code était déjà en
production. Deux conséquences, énoncées dans chaque fichier :

- les options écartées ont été comparées **sur dossier**, sans prototype de
  chacune ni campagne de mesure — aucun chiffre de performance comparée n'est
  avancé, et aucun ne doit l'être ;
- les **conséquences**, en revanche, ne sont pas théoriques : elles sont
  constatées dans le code et en exploitation. Chaque ADR comporte une section
  « Conséquences négatives » qui recense les limites et les défauts connus du
  choix, y compris ceux encore ouverts.

Un ADR qui n'énumère que des avantages n'a aucune valeur. Ceux-ci disent aussi
ce que chaque décision a coûté.

---

## Format retenu

Chaque document suit la même structure :

| Section | Contenu |
|---|---|
| **En-tête** | Statut, date de décision, date de rédaction, décideurs, périmètre |
| **Contexte** | Le besoin et les contraintes, tels qu'ils se posaient |
| **Options envisagées** | Chaque candidat, ses atouts, et le motif précis de son rejet |
| **Décision** | Ce qui est retenu, et l'argument décisif |
| **Conséquences** | Positives, négatives, et ce qu'il faudrait pour revenir en arrière |
| **Références** | Fichiers du dépôt concernés, décisions liées |

La section « ce qu'il faudrait pour revenir en arrière » n'est pas dans le
format standard. Elle a été ajoutée parce qu'elle est souvent l'information la
plus utile : elle indique le coût réel d'un changement d'avis.

---

## Ajouter une décision

1. Créer `ADR-00N-sujet.md` en reprenant la structure ci-dessus, sans sauter
   de numéro — la numérotation est chronologique et définitive.
2. Renseigner le statut : `Proposée`, `Acceptée`, `Rejetée`, ou
   `Remplacée par ADR-00X`.
3. **Ne jamais supprimer ni réécrire un ADR existant.** Une décision revenue
   sur passe en `Remplacée par`, et le nouveau document explique ce qui a
   changé. L'historique des raisonnements fait toute la valeur du dossier.
4. Ajouter la ligne correspondante au tableau de ce fichier.
