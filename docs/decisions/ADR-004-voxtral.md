# ADR-004 — Voxtral (Mistral AI) plutôt qu'AssemblyAI ou Deepgram

| | |
|---|---|
| **Statut** | Acceptée — en production |
| **Date de la décision** | Juillet 2026 |
| **Date de rédaction** | 26 août 2026 |
| **Décideurs** | Enzo Bandinu, Théo Channarond, Mathis Fonbonne, Lydie Havugimana |
| **Périmètre** | `backend/app/services/voxtral_service.py` |

> **Note de méthode.** Document rédigé a posteriori. Comparaison menée **sur
> dossier**, sans campagne de test comparative sur un corpus commun : aucun
> chiffre de taux d'erreur mot n'est avancé ici, et aucun ne doit l'être en
> soutenance. Les conséquences décrites sont constatées dans le code, dont une
> fonctionnalité annoncée qui n'est pas opérationnelle à ce jour.

---

## Contexte

La transcription est le cœur d'Auris : sans elle, il n'y a ni compte rendu ni
produit. Le service reçoit un fichier audio — dictaphone ou captation de
réunion vidéo (ADR-007) — et doit en produire un texte exploitable.

Les exigences :

- **le français en premier lieu**, l'usage visé étant des réunions
  professionnelles francophones ;
- **des enregistrements longs** : une réunion dure couramment de trente minutes
  à une heure, d'où un délai d'attente fixé à 300 secondes
  (`VOXTRAL_TIMEOUT_SEC`) ;
- **du traitement par lot, non temps réel** : l'utilisateur enregistre puis
  dépose ; rien n'exige une transcription à la volée ;
- **l'identification des locuteurs**, prévue au modèle de données
  (colonne `diarization`) ;
- **la confidentialité** : l'audio envoyé au moteur contient l'intégralité des
  propos tenus en réunion. C'est la donnée la plus sensible du système.

Ce dernier point est décisif, et il prolonge directement l'ADR-003. Il aurait
été incohérent de refuser un hébergeur soumis au droit américain pour le
*stockage* des fichiers, puis d'envoyer le *contenu* de ces mêmes réunions à un
prestataire relevant de ce droit.

---

## Options envisagées

### Option A — Deepgram

Un moteur de reconnaissance vocale reconnu, aux performances de latence
solides, avec une diarisation mature proposée en paramètre de premier plan et
une offre de transcription en flux continu.

Sur le plan fonctionnel, c'est probablement l'option la plus aboutie des trois
pour l'identification des locuteurs.

**Écarté :** société de droit américain. Lui transmettre l'audio intégral de
réunions professionnelles ramenait exactement l'exposition juridique que
l'ADR-003 visait à éviter — et sur une donnée plus sensible encore que le
stockage.

### Option B — AssemblyAI

Également très complet, avec une couche d'analyse au-delà de la simple
transcription : détection de sujets, occultation de données personnelles,
résumé intégré.

Cette richesse fonctionnelle était réelle, mais partiellement redondante avec
ce qu'Auris construit par ailleurs : le résumé structuré est produit par
Mistral Small à partir du texte, avec des consignes propres au produit.

**Écarté :** même motif juridique que Deepgram, sans compensation suffisante.

### Option C — Voxtral (Mistral AI)

Modèle de transcription de Mistral AI, société française, appelé via l'API
`https://api.mistral.ai/v1/audio/transcriptions` avec le modèle
`voxtral-mini-latest`.

- **Opérateur européen**, cohérent avec l'hébergement retenu à l'ADR-003 :
  l'audio, les transcriptions, les résumés et les identités restent sous droit
  européen, sans exception.
- **Le français comme langue de premier plan**, s'agissant d'un laboratoire
  français — attente qualitative, non mesurée par nos soins.
- **Un seul fournisseur pour deux besoins.** La même clé `MISTRAL_API_KEY` et
  la même URL `MISTRAL_API_URL` servent à la transcription *et* à la génération
  du compte rendu (`mistral-small-latest`, via `/chat/completions` dans
  `mistral_service.py`). Un contrat, une facture, une intégration, un seul
  service à surveiller.
- **Coût contenu** pour la version *Mini*, ce qui compte sur un projet sans
  budget.

---

## Décision

**Nous retenons Voxtral Mini de Mistral AI**, appelé en HTTP asynchrone depuis
`backend/app/services/voxtral_service.py`.

Le motif décisif est la cohérence de souveraineté avec l'ADR-003 : l'audio
d'une réunion est la donnée la plus intime que traite Auris, et la faire sortir
du périmètre juridique européen aurait vidé de son sens le choix d'hébergement.

Le motif secondaire, mais très concret au quotidien, est la consolidation chez
un fournisseur unique pour la transcription et le résumé.

Nous assumons de renoncer aux fonctions avancées de Deepgram et d'AssemblyAI —
en particulier une diarisation mature, qui est le vrai point faible de ce
choix (voir ci-dessous).

---

## Conséquences

### Positives

- Chaîne de traitement entièrement européenne, de l'enregistrement au compte
  rendu.
- Une seule intégration, une seule clé, une seule facture pour les deux usages
  d'intelligence artificielle du produit.
- Appels asynchrones (`httpx.AsyncClient`), compatibles avec le modèle
  d'exécution retenu à l'ADR-001.
- Une politique de reprise sur erreur a pu être écrite au-dessus de l'API :
  `transcribe_audio_with_backoff()` réessaie avec un délai exponentiel
  (1s, 2s, 4s) sur les erreurs transitoires, et **ne réessaie pas** sur les
  erreurs définitives — clé absente, audio vide, transcription vide. Le nombre
  de tentatives est conservé en base (`retry_count`).

### Négatives

- **La diarisation n'est pas fonctionnelle aujourd'hui.** C'est la conséquence
  la plus lourde de ce choix, et elle est encore ouverte. Le modèle de données
  prévoit la colonne `diarization`, un service de normalisation existe
  (`diarization_parser_service.py`, qui transforme `SPEAKER_00` en
  « Intervenant 1 »), et l'interface sait l'afficher
  (`DiarizationDisplay.tsx`). Mais **rien ne relie ces trois pièces** :
  `transcribe_audio()` ne lit aucun champ de segments dans la réponse de
  Voxtral, `parse_diarization()` n'est appelée nulle part, et la colonne reste
  donc toujours vide. Côté interface, l'affichage est conditionné à la présence
  de segments — la section ne s'affiche jamais, sans erreur visible. C'est
  précisément le terrain sur lequel Deepgram était le plus fort.
- **Un fournisseur unique est aussi un point de défaillance unique.** C'est le
  revers exact de l'avantage revendiqué plus haut : une indisponibilité de
  Mistral interrompt à la fois la transcription et la génération des comptes
  rendus. Les deux dépendent de la même clé et du même service.
- **Pas de transcription en flux continu.** Le modèle retenu traite par lot.
  Une évolution vers une transcription affichée pendant la réunion supposerait
  de changer de moteur, ou d'en ajouter un second.
- **Moins de fonctions annexes** que la concurrence : ni occultation
  automatique des données personnelles, ni détection de sujets. Tout ce qui
  dépasse la transcription brute est à construire.
- **Un traitement long à absorber.** Cinq minutes d'attente maximale imposent
  la réponse `202 Accepted` et le traitement en arrière-plan décrits à
  l'ADR-001.

### Ce qu'il faudrait pour revenir en arrière

Le changement de moteur est **circonscrit à un fichier**.
`voxtral_service.py` expose deux fonctions et retourne un dictionnaire
normalisé (`text`, `language`, `model`, `processing_ms`). Adopter Deepgram ou
AssemblyAI reviendrait à réécrire ce module en conservant ce contrat ; les
appelants, le modèle de données et l'interface ne bougeraient pas.

C'est d'ailleurs la voie à retenir si la diarisation devient une exigence
ferme : les concurrents écartés la fournissent en paramètre standard.

---

## Références

- Code : `backend/app/services/voxtral_service.py`,
  `backend/app/services/mistral_service.py`,
  `backend/app/services/diarization_parser_service.py`
- Réglages : `backend/app/core/database.py` (`VOXTRAL_MODEL`,
  `VOXTRAL_TIMEOUT_SEC`, `MAX_RETRY_COUNT`)
- Décisions liées : [ADR-003](ADR-003-ovh.md) (souveraineté des données),
  [ADR-001](ADR-001-fastapi.md) (traitement asynchrone),
  [ADR-007](ADR-007-vexa.md) (origine de l'audio en mode vidéo)
