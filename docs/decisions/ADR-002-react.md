# ADR-002 — React plutôt qu'Angular

| | |
|---|---|
| **Statut** | Acceptée — en production |
| **Date de la décision** | Juillet 2026, au démarrage du projet |
| **Date de rédaction** | 26 août 2026 |
| **Décideurs** | Enzo Bandinu, Théo Channarond, Mathis Fonbonne, Lydie Havugimana |
| **Périmètre** | `frontend/` |

> **Note de méthode.** Document rédigé a posteriori. Les deux options ont été
> comparées **sur dossier**, sans prototype de chacune. Les conséquences
> décrites plus bas sont, elles, constatées dans le code — y compris un défaut
> qui a atteint la production.

---

## Contexte

L'interface d'Auris est une application monopage qui consomme l'API JSON du
backend (ADR-001). Elle compte aujourd'hui sept pages (connexion, consentement,
tableau de bord, dictaphone, mode vidéo, détail de réunion), une quinzaine de
composants d'interface et huit crochets métier.

Les besoins qui pèsent réellement sur le choix :

- **Capture audio dans le navigateur** via `MediaRecorder`
  (`frontend/src/hooks/useAudioRecorder.ts`) ;
- **Fonctionnement hors ligne** avec stockage IndexedDB des enregistrements et
  synchronisation différée (`services/audioStorage.ts`, `hooks/useOfflineSync.ts`) ;
- **Interrogation périodique** de l'état des traitements longs — transcription,
  résumé, bot vidéo — puisque le backend répond `202 Accepted` et travaille en
  arrière-plan ;
- **Authentification par jeton Keycloak** (ADR-005), le front devant porter le
  jeton sur chaque appel.

Deux contraintes de projet encadrent la décision : une équipe de quatre
personnes, et un calendrier de l'ordre du trimestre. La difficulté attendue du
projet se situait dans la chaîne audio et le traitement asynchrone, pas dans
l'interface.

---

## Options envisagées

### Option A — Angular

Un framework complet, structuré, écrit en TypeScript.

Ses atouts correspondent à un vrai besoin d'équipe : une architecture imposée
plutôt que négociée, l'injection de dépendances, `HttpClient` avec ses
intercepteurs, un routeur officiel, des formulaires réactifs, une interface en
ligne de commande qui génère les fichiers aux bons endroits. Sur un projet à
plusieurs mains, cette uniformité a de la valeur — chacun écrit le même code.

Le coût est ailleurs. Angular demande d'assimiler RxJS et la programmation par
flux, ses propres conventions de modules et de composants, et son cycle de
détection de changements. C'est un investissement qui se rentabilise sur la
durée et sur une application vaste ; il est plus difficile à amortir sur un
trimestre, pour une application de sept pages, quand le temps disponible doit
aller à la capture audio et au mode hors ligne.

**Écarté :** la structure imposée aurait été utile, mais la courbe
d'apprentissage tombait au mauvais moment du projet.

### Option B — React

Une bibliothèque d'interface, pas un framework : elle traite le rendu des
composants et rien d'autre.

- **Une surface conceptuelle réduite.** Des composants, des propriétés, et les
  crochets `useState` / `useEffect`. C'est suffisant pour toute l'application :
  le dossier `frontend/src/store/` est resté vide — aucune bibliothèque de
  gestion d'état globale n'a été nécessaire, les huit crochets métier de
  `frontend/src/hooks/` couvrent l'ensemble des besoins.
- **Un écosystème très large.** Chaque besoin rencontré avait une réponse
  documentée et éprouvée.
- **Un outillage immédiat avec Vite**, qui a aussi permis de servir le front en
  développement avec rechargement à chaud, puis de produire un bundle statique
  servi par nginx en production (`frontend/Dockerfile`).
- **TypeScript disponible**, et effectivement utilisé partout dans le projet.

---

## Décision

**Nous retenons React 19**, avec TypeScript, Vite, React Router 7 et Tailwind
CSS 4. Les tests unitaires utilisent Vitest et Testing Library, les tests de
bout en bout Playwright.

Le raisonnement tient en une phrase : sur un projet court, le budget
d'apprentissage devait aller au métier — capture audio, hors ligne, traitements
asynchrones — et non au framework d'interface. React demande d'apprendre peu
avant de produire ; Angular demande d'apprendre beaucoup avant de produire, et
rend ensuite la suite plus cadrée.

Ce raisonnement est valable pour Auris. Il ne l'est pas universellement : sur
une application plus vaste, ou destinée à être reprise par des équipes
successives, la structure imposée par Angular deviendrait un avantage net.

---

## Conséquences

### Positives

- Aucune bibliothèque de gestion d'état n'a été nécessaire ; l'état vit dans
  les crochets, au plus près de son usage.
- L'écriture des composants d'interface a été rapide, ce qui a permis de
  concentrer l'effort sur `useAudioRecorder` et la synchronisation hors ligne.
- L'application se construit en un bundle statique, donc s'héberge derrière
  nginx sans exécution de code côté serveur.
- Les tests de composants sont directs avec Testing Library.

### Négatives

Elles découlent toutes du même fait : **React n'impose rien, donc l'équipe doit
imposer elle-même ses conventions — et sur ce projet, cela n'a pas toujours
tenu.**

- **L'absence de couche HTTP officielle a coûté un bug de production.**
  `frontend/src/services/api.ts` est un enrobage de `fetch` écrit à la main. Il
  ajoute le jeton d'authentification, mais **ne traite ni la réponse 401 ni le
  renouvellement du jeton Keycloak**. Conséquence : passé la durée de vie du
  jeton d'accès, l'application cessait simplement de fonctionner jusqu'à
  reconnexion. Avec Angular, « renouveler le jeton sur 401 » est le cas d'école
  d'un `HttpInterceptor` — documenté, attendu, difficile à oublier. Avec React,
  c'est un enrobage que quelqu'un doit penser à écrire. *Corrigé depuis sur la
  branche `fix/keycloak-token-refresh` (verrou anti-concurrence, 12 tests), en
  attente de fusion.*
- **Du code mort s'est installé sans que rien ne le signale.** Toujours dans
  `api.ts`, la fonction `authHeaders()` duplique la logique d'`apiFetch` et
  n'est plus appelée.
- **Chaque crochet réimplémente à la main** son état de chargement, son état
  d'erreur et son annulation — le motif `let cancelled = false` se répète à
  l'identique dans `useMeetings`, `useMeetingDetail`, `useTranscriptionStatus`
  et les autres. Une bibliothèque de récupération de données comme TanStack
  Query supprimerait cette duplication.
- **Les choix de dépendances sont à la charge de l'équipe** — React Router,
  outillage de test, gestion des formulaires — et suivent chacun leur propre
  rythme de versions.

### Ce qu'il faudrait pour revenir en arrière

Un changement de bibliothèque d'interface signifierait réécrire l'intégralité
de `frontend/src/`. Seuls survivraient les appels d'API — le contrat OpenAPI du
backend est indépendant du front — et la logique pure de
`services/audioStorage.ts`. Autrement dit : ce n'est pas réversible à coût
raisonnable, c'est la décision la plus engageante des sept.

---

## Références

- Code : `frontend/src/`, `frontend/package.json`, `frontend/Dockerfile`
- Défaut cité : `frontend/src/services/api.ts`, corrigé sur
  `fix/keycloak-token-refresh`
- Décisions liées : [ADR-001](ADR-001-fastapi.md) (API JSON consommée),
  [ADR-005](ADR-005-keycloak.md) (jeton porté par le front)
