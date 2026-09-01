# ADR-005 — Keycloak plutôt qu'une authentification maison

| | |
|---|---|
| **Statut** | Acceptée — en production |
| **Date de la décision** | Juillet 2026 |
| **Date de rédaction** | 26 août 2026 |
| **Décideurs** | Enzo Bandinu, Théo Channarond, Mathis Fonbonne, Lydie Havugimana |
| **Périmètre** | `backend/app/core/security.py`, `infra/keycloak-realm.json`, `frontend/src/App.tsx` |

> **Note de méthode.** Document rédigé a posteriori. Comparaison menée **sur
> dossier**. La section « Conséquences » recense des écarts d'intégration
> constatés dans le code actuel : déléguer l'authentification à Keycloak ne
> rend pas l'intégration automatiquement correcte, et il serait malhonnête de
> laisser croire l'inverse.

---

## Contexte

Auris traite des enregistrements de réunions professionnelles. L'accès à un
compte donne accès à l'audio et aux comptes rendus de toutes les réunions de
son propriétaire : la compromission d'un compte est, ici, une fuite de données
personnelles au sens du RGPD.

Les besoins :

- inscription, connexion, déconnexion ;
- stockage des mots de passe conforme à l'état de l'art ;
- réinitialisation de mot de passe ;
- protection contre les attaques par force brute ;
- une identité utilisateur exploitable côté API pour cloisonner les données ;
- une porte ouverte vers l'authentification unique en entreprise, cible
  commerciale naturelle du produit.

Contrainte structurante : **une équipe de quatre étudiants sur un trimestre**,
dont aucun n'est spécialiste de la sécurité applicative.

---

## Options envisagées

### Option A — Authentification maison

Une table `users` avec un mot de passe haché, des routes d'inscription et de
connexion, et un jeton JWT signé par l'application.

C'est l'option qui paraît la plus simple, et c'est un piège classique. Une
authentification correcte ne se limite pas à hacher un mot de passe : il faut
choisir et paramétrer une fonction de dérivation adaptée puis la faire évoluer,
gérer la réinitialisation par courriel avec des jetons à usage unique et à
durée limitée, verrouiller les comptes après des tentatives répétées, prévenir
l'énumération de comptes, faire tourner les clés de signature, révoquer les
jetons, résister aux attaques temporelles sur la comparaison.

Chacun de ces points est un défaut de sécurité connu et documenté quand il est
mal traité. Les traiter tous demande une compétence que l'équipe n'a pas, et
un temps qui n'existe pas dans le calendrier.

Le rapport bénéfice/risque est défavorable : c'est le composant où une erreur
coûte le plus cher, et c'est celui où nous serions le moins compétents.

**Écarté.**

### Option B — Un service d'authentification en ligne (Auth0, Cognito)

Techniquement excellent, opéré par des spécialistes, sans serveur à maintenir.

Mais ce sont des services d'éditeurs américains, ce qui ramène l'exposition
juridique écartée à l'ADR-003 — et cette fois sur les identités des
utilisateurs. La tarification à l'utilisateur actif est par ailleurs
incompatible avec un projet sans budget.

**Écarté :** incohérent avec la ligne de souveraineté retenue pour
l'hébergement et la transcription.

### Option C — Keycloak

Serveur d'identité libre, sous licence Apache 2, adossé à la fondation
CNCF/Red Hat, déployable dans notre propre infrastructure.

- **Les mécanismes délicats sont fournis et éprouvés** : hachage des mots de
  passe, réinitialisation, vérification d'adresse, verrouillage. Le fichier
  `infra/keycloak-realm.json` active explicitement
  `bruteForceProtected`, `resetPasswordAllowed`, `registrationAllowed` et
  `loginWithEmailAllowed` — quatre fonctionnalités obtenues par configuration,
  et non par du code à écrire et à tester.
- **Protocoles standard** : OpenID Connect et OAuth 2. Le backend n'a pas de
  session à gérer ; il valide une signature RS256 à partir des clés publiques
  exposées par Keycloak (`backend/app/core/security.py`).
- **Le backend ne voit jamais un mot de passe.** Il ne peut donc pas le
  divulguer. C'est un argument RGPD direct : la surface de compromission des
  identifiants se réduit à un seul composant.
- **Le realm est versionné** (`infra/keycloak-realm.json`), donc les
  environnements sont reproductibles — c'est ce qui permet au guide
  d'installation de fonctionner.
- **Chemin d'évolution ouvert** : authentification unique d'entreprise,
  fédération LDAP, double facteur, connexion via un fournisseur tiers — sans
  modifier une ligne d'Auris.
- **Auto-hébergeable**, donc cohérent avec l'ADR-003.

---

## Décision

**Nous retenons Keycloak 24**, déployé en conteneur aux côtés du reste de la
pile, avec un realm `auris` versionné dans le dépôt.

Le raisonnement est celui du rapport entre le coût d'une erreur et notre
compétence. L'authentification est le composant où une faute se paie le plus
cher, et celui où une équipe de quatre étudiants a le moins de chances de faire
mieux qu'un logiciel éprouvé par des milliers de déploiements. Réécrire ce que
Keycloak fournit aurait été du travail à haut risque et sans valeur pour
l'utilisateur.

Le realm définit deux clients : `auris-frontend`, client public utilisant le
flux de code d'autorisation, et `auris-backend`, client confidentiel qui ne
fait que valider des jetons.

---

## Conséquences

### Positives

- Aucun mot de passe n'est stocké, ni même vu, par le code d'Auris. La table
  `users` ne contient qu'un `keycloak_id`, une adresse et un nom.
- La protection contre la force brute, la réinitialisation de mot de passe et
  la vérification d'adresse fonctionnent sans code de notre part.
- Le backend est sans état : `Depends(get_current_user)` suffit à protéger une
  route, et il n'y a aucun magasin de sessions à exploiter ou à répliquer.
- Les environnements sont reproductibles par import du realm.
- Le produit peut être proposé à une entreprise disposant déjà d'un annuaire,
  sans redéveloppement.

### Négatives

- **Un service lourd de plus sur un VPS unique.** Keycloak est une application
  Java dont l'empreinte mémoire et le temps de démarrage dépassent largement
  ceux du backend — au point que sa sonde de santé en production doit tolérer
  90 secondes de démarrage. Sur une machine qui héberge déjà la base, l'API, le
  front et le proxy, ce n'est pas neutre.
- **Le déploiement derrière un proxy inverse a coûté une panne silencieuse.**
  En production, Keycloak est servi sous le préfixe `/auth`. Le backend
  interrogeait ses clés publiques à `/realms/...` au lieu de
  `/auth/realms/...` : la récupération échouait, et **toutes les routes
  authentifiées tombaient**, sans message explicite. *Corrigé sur la branche de
  déploiement, en attente de fusion.*
- **Déléguer l'authentification ne dispense pas d'intégrer correctement — et
  notre intégration comporte des écarts.** Ils sont réels et documentés ici
  plutôt que découverts en soutenance :
  - **Le flux de code d'autorisation est utilisé sans PKCE.** L'URL construite
    dans `frontend/src/pages/LoginPage.tsx` ne porte pas de `code_challenge`,
    et l'échange dans `App.tsx` pas de `code_verifier`. Pour un client public,
    PKCE est la recommandation courante et devient obligatoire avec OAuth 2.1.
  - **Le paramètre `state` est absent**, donc la redirection n'est pas
    protégée contre une falsification de requête.
  - **Les jetons sont conservés dans `localStorage`**, donc lisibles par tout
    script s'exécutant sur la page. Un stockage en mémoire, ou un cookie
    `HttpOnly` posé par le backend, réduirait cette exposition.
  - **L'audience du jeton n'est pas vérifiée** : `verify_aud: False` dans
    `security.py`. Un jeton émis par le même realm pour un autre client serait
    accepté.
  - **Le client public `auris-frontend` a `directAccessGrantsEnabled: true`**,
    c'est-à-dire le flux par mot de passe, alors que l'application ne
    l'utilise pas. C'est une surface d'attaque ouverte sans usage.
- **Une console d'administration à apprendre**, et un realm dont les
  modifications manuelles doivent être réexportées pour rester versionnées.
- **Des montées de version à assurer** : Keycloak évolue vite et ses versions
  majeures introduisent des ruptures — le port de supervision, par exemple, a
  changé entre les versions 24 et 25.

### Ce qu'il faudrait pour revenir en arrière

Le backend ne dépend de Keycloak qu'à travers `security.py`, qui valide un JWT
signé en RS256 à partir d'un jeu de clés publiques — un contrat standard.
Basculer vers un autre serveur OpenID Connect reviendrait à changer une URL.
Revenir à une authentification maison serait en revanche un chantier complet,
et un recul en matière de sécurité.

---

## Références

- Code : `backend/app/core/security.py`, `backend/app/api/v1/auth.py`,
  `frontend/src/pages/LoginPage.tsx`, `frontend/src/App.tsx`
- Configuration : `infra/keycloak-realm.json`, `infra/docker-compose.prod.yml`
- Décisions liées : [ADR-001](ADR-001-fastapi.md) (validation par dépendance),
  [ADR-002](ADR-002-react.md) (renouvellement du jeton côté front),
  [ADR-003](ADR-003-ovh.md) (auto-hébergement)
