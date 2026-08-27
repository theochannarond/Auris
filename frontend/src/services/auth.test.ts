import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import {
  storeTokens,
  clearTokens,
  getAccessToken,
  getValidAccessToken,
  refreshAccessToken,
} from "./auth";

const VALID_RESPONSE = {
  access_token:  "nouveau-jeton",
  refresh_token: "nouveau-refresh",
  expires_in:    300,
};

function mockTokenEndpoint(response: unknown, ok = true) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok,
    json: async () => response,
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

beforeEach(() => {
  localStorage.clear();
  vi.unstubAllGlobals();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("stockage des jetons", () => {
  it("conserve le jeton de rafraîchissement et la date d'expiration", () => {
    const avant = Date.now();
    storeTokens(VALID_RESPONSE);

    expect(getAccessToken()).toBe("nouveau-jeton");
    expect(localStorage.getItem("refresh_token")).toBe("nouveau-refresh");

    const expiration = Number(localStorage.getItem("access_token_expires_at"));
    expect(expiration).toBeGreaterThanOrEqual(avant + 300_000);
  });

  it("garde le jeton de rafraîchissement précédent si l'échange n'en renvoie pas", () => {
    storeTokens(VALID_RESPONSE);
    storeTokens({ access_token: "jeton-suivant", expires_in: 300 });

    expect(localStorage.getItem("refresh_token")).toBe("nouveau-refresh");
  });

  it("efface les trois entrées à la fermeture de session", () => {
    storeTokens(VALID_RESPONSE);
    clearTokens();

    expect(localStorage.getItem("access_token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
    expect(localStorage.getItem("access_token_expires_at")).toBeNull();
  });
});

describe("obtention d'un jeton exploitable", () => {
  it("renvoie le jeton en place tant qu'il n'est pas près d'expirer", async () => {
    storeTokens(VALID_RESPONSE);
    const fetchMock = mockTokenEndpoint(VALID_RESPONSE);

    await expect(getValidAccessToken()).resolves.toBe("nouveau-jeton");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("renouvelle le jeton lorsqu'il approche de son expiration", async () => {
    storeTokens({ access_token: "vieux-jeton", refresh_token: "refresh", expires_in: 10 });
    const fetchMock = mockTokenEndpoint(VALID_RESPONSE);

    // 10 secondes de durée de vie : la marge de sécurité de 30 secondes place
    // ce jeton dans la zone de renouvellement dès maintenant.
    await expect(getValidAccessToken()).resolves.toBe("nouveau-jeton");
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it("ne renvoie rien quand aucune session n'est ouverte", async () => {
    await expect(getValidAccessToken()).resolves.toBeNull();
  });

  it("laisse passer un jeton dépourvu de date d'expiration", async () => {
    // Session ouverte avant la mise en place du renouvellement : on ne
    // déconnecte pas d'office, le serveur tranchera.
    localStorage.setItem("access_token", "jeton-hérité");
    const fetchMock = mockTokenEndpoint(VALID_RESPONSE);

    await expect(getValidAccessToken()).resolves.toBe("jeton-hérité");
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("renouvellement", () => {
  it("échoue sans jeton de rafraîchissement, sans appeler Keycloak", async () => {
    const fetchMock = mockTokenEndpoint(VALID_RESPONSE);

    await expect(refreshAccessToken()).resolves.toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("échoue proprement quand Keycloak refuse le jeton de rafraîchissement", async () => {
    storeTokens(VALID_RESPONSE);
    mockTokenEndpoint({ error: "invalid_grant" }, false);

    await expect(refreshAccessToken()).resolves.toBeNull();
  });

  it("échoue proprement quand le réseau est coupé", async () => {
    storeTokens(VALID_RESPONSE);
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("réseau injoignable")));

    await expect(refreshAccessToken()).resolves.toBeNull();
  });

  it("n'émet qu'un seul échange pour plusieurs appels simultanés", async () => {
    storeTokens(VALID_RESPONSE);

    // Le point sensible : Keycloak invalide le jeton de rafraîchissement dès
    // le premier échange. Sans verrou, cinq appels concurrents en lanceraient
    // cinq, et les quatre derniers déconnecteraient l'utilisateur.
    const fetchMock = mockTokenEndpoint(VALID_RESPONSE);

    const results = await Promise.all([
      refreshAccessToken(),
      refreshAccessToken(),
      refreshAccessToken(),
      refreshAccessToken(),
      refreshAccessToken(),
    ]);

    expect(fetchMock).toHaveBeenCalledOnce();
    expect(results).toEqual(Array(5).fill("nouveau-jeton"));
  });

  it("autorise un nouvel échange une fois le précédent terminé", async () => {
    storeTokens(VALID_RESPONSE);
    const fetchMock = mockTokenEndpoint(VALID_RESPONSE);

    await refreshAccessToken();
    await refreshAccessToken();

    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
