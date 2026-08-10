import type { Page } from '@playwright/test'

/**
 * Simulacres réseau pour les tests E2E.
 *
 * Ni le backend, ni Keycloak, ni les API externes ne tournent pendant ces
 * tests : chaque appel est intercepté et servi par une réponse figée. Ce qui
 * est validé ici, c'est le comportement du navigateur — routage, composants,
 * enchaînement des états — pas la chaîne de traitement réelle.
 */

/**
 * Serveur d'autorisation Keycloak.
 *
 * On répond une page factice pour que la redirection aboutisse : l'URL
 * demandée reste ainsi inspectable, ce qui permet de vérifier que
 * l'application initie correctement le flux OIDC.
 */
export async function mockKeycloakAuth(page: Page) {
  await page.route('**/protocol/openid-connect/auth*', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'text/html',
      body: '<html><body><h1>Keycloak</h1></body></html>',
    })
  )
}

/** Enregistrement du consentement RGPD. */
export async function mockConsent(page: Page) {
  await page.route('**/api/v1/consents', (route) =>
    route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({
        id: '11111111-1111-1111-1111-111111111111',
        given_at: '2026-08-11T09:00:00',
      }),
    })
  )
}
