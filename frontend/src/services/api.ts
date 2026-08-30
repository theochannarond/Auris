import { getAccessToken, getValidAccessToken, refreshAccessToken, endSession } from "./auth";

/**
 * Point de passage unique de tous les appels authentifiés à l'API.
 *
 * Le jeton est renouvelé avant l'envoi s'il approche de son expiration, et une
 * seconde fois si le serveur le rejette malgré tout. En cas d'échec, la session
 * est close proprement plutôt que de laisser l'application échouer en silence.
 */
export async function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const send = (token: string | null) => {
    const headers: Record<string, string> = {};

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    // Ne pas forcer Content-Type pour FormData — le navigateur le gère automatiquement
    if (!(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }

    return fetch(url, {
      ...options,
      headers: {
        ...headers,
        ...(options.headers || {}),
      },
    });
  };

  const token = await getValidAccessToken();

  // Un jeton existait mais n'a pas pu être renouvelé : la session est perdue.
  // Sans ce cas, la requête partait SANS en-tête Authorization, le serveur
  // répondait 403 — et non 401 — si bien que le renouvellement ci-dessous
  // n'était jamais tenté et la session jamais fermée. L'utilisateur restait
  // devant un écran qui échouait en boucle, sans jamais revenir à la connexion.
  if (!token && getAccessToken()) {
    endSession();
    return send(null);
  }

  const response = await send(token);

  // Pas de jeton du tout : appel public, ou utilisateur non connecté. Rien à
  // renouveler, on rend la réponse telle quelle.
  if (response.status !== 401) return response;

  // Le jeton paraissait valide et a pourtant été refusé : horloge décalée,
  // session fermée côté Keycloak, ou jeton révoqué. On tente un renouvellement,
  // une seule fois — s'obstiner ne ferait que retarder l'inévitable.
  const renewedToken = await refreshAccessToken();

  if (!renewedToken) {
    endSession();
    return response;
  }

  return send(renewedToken);
}
