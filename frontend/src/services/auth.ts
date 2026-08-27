/**
 * Gestion du cycle de vie de la session Keycloak.
 *
 * Les jetons d'accès Keycloak durent quelques minutes. Sans renouvellement,
 * l'application continuait de s'afficher normalement pendant que chaque appel
 * échouait en silence : l'utilisateur restait devant un écran mort, sans
 * message ni retour vers la connexion. C'est ce que ce module corrige.
 */

const ACCESS_TOKEN_KEY  = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";
const EXPIRES_AT_KEY    = "access_token_expires_at";

const KEYCLOAK_URL       = import.meta.env.VITE_KEYCLOAK_URL       || "http://localhost:8080";
const KEYCLOAK_REALM     = import.meta.env.VITE_KEYCLOAK_REALM     || "auris";
const KEYCLOAK_CLIENT_ID = import.meta.env.VITE_KEYCLOAK_CLIENT_ID || "auris-frontend";

const TOKEN_ENDPOINT =
  `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token`;

// On renouvelle un peu avant l'expiration réelle plutôt qu'après : une requête
// partie à la dernière seconde arriverait sinon avec un jeton déjà périmé, le
// trajet réseau n'étant pas instantané.
const EXPIRY_MARGIN_MS = 30_000;

// Durée retenue quand Keycloak ne renvoie pas expires_in. Volontairement
// courte : mieux vaut un renouvellement inutile qu'un jeton cru valable
// beaucoup plus longtemps qu'il ne l'est.
const DEFAULT_LIFETIME_SEC = 60;

export interface TokenResponse {
  access_token:   string;
  refresh_token?: string;
  expires_in?:    number;
}

export function storeTokens(data: TokenResponse): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, data.access_token);

  // Keycloak renvoie un nouveau jeton de rafraîchissement à chaque échange.
  // S'il est absent, on garde le précédent plutôt que d'effacer le seul moyen
  // de prolonger la session.
  if (data.refresh_token) {
    localStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token);
  }

  const lifetimeMs = (data.expires_in ?? DEFAULT_LIFETIME_SEC) * 1000;
  localStorage.setItem(EXPIRES_AT_KEY, String(Date.now() + lifetimeMs));
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(EXPIRES_AT_KEY);
}

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

function isExpired(): boolean {
  const expiresAt = Number(localStorage.getItem(EXPIRES_AT_KEY));

  // Session ouverte avant la mise en place de ce module : aucune date
  // d'expiration enregistrée. On laisse passer la requête — un éventuel 401
  // déclenchera le renouvellement, ce qui évite de déconnecter d'office
  // quelqu'un dont le jeton est peut-être encore valable.
  if (!expiresAt) return false;

  return Date.now() >= expiresAt - EXPIRY_MARGIN_MS;
}

// Un seul renouvellement à la fois. Sans ce verrou, une page qui déclenche
// cinq appels simultanés lancerait cinq échanges concurrents ; Keycloak
// invalide le jeton de rafraîchissement dès le premier, et les quatre autres
// échoueraient — déconnectant l'utilisateur alors que tout allait bien.
let refreshInFlight: Promise<string | null> | null = null;

export function refreshAccessToken(): Promise<string | null> {
  if (refreshInFlight) return refreshInFlight;

  refreshInFlight = performRefresh().finally(() => {
    refreshInFlight = null;
  });

  return refreshInFlight;
}

async function performRefresh(): Promise<string | null> {
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
  if (!refreshToken) return null;

  try {
    const res = await fetch(TOKEN_ENDPOINT, {
      method:  "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body:    new URLSearchParams({
        grant_type:    "refresh_token",
        client_id:     KEYCLOAK_CLIENT_ID,
        refresh_token: refreshToken,
      }),
    });

    if (!res.ok) return null;

    const data: TokenResponse = await res.json();
    if (!data.access_token) return null;

    storeTokens(data);
    return data.access_token;
  } catch {
    // Réseau coupé : la session n'est pas forcément perdue, mais on ne peut
    // rien affirmer. L'appelant décidera quoi faire de ce null.
    return null;
  }
}

/** Renvoie un jeton exploitable, en le renouvelant au besoin. */
export async function getValidAccessToken(): Promise<string | null> {
  const token = getAccessToken();
  if (!token) return null;
  if (!isExpired()) return token;

  return refreshAccessToken();
}

/**
 * Session définitivement perdue : on nettoie et on renvoie à la connexion.
 *
 * C'est le comportement qui manquait. Laisser l'utilisateur sur une page qui
 * échoue silencieusement à chaque clic est bien pire que de lui redemander de
 * se connecter.
 */
export function endSession(): void {
  clearTokens();

  // Le test sur le chemin évite une boucle de redirections si l'appel qui a
  // échoué venait de la page de connexion elle-même.
  if (window.location.pathname !== "/") {
    window.location.replace("/");
  }
}
