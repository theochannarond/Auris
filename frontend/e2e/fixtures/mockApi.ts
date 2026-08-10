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

export const MEETING_ID = '22222222-2222-2222-2222-222222222222'

/**
 * Création d'une réunion (dictaphone).
 *
 * Le motif attrape aussi le GET du dashboard : on rend la main via fallback()
 * pour tout ce qui n'est pas un POST, afin de ne pas court-circuiter les
 * autres interceptions enregistrées par le test.
 */
export async function mockCreateMeeting(page: Page) {
  await page.route('**/api/v1/meetings', (route) => {
    if (route.request().method() !== 'POST') return route.fallback()

    return route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({
        id: MEETING_ID,
        owner_id: '33333333-3333-3333-3333-333333333333',
        title: 'Réunion du 11/08/2026',
        mode: 'dictaphone',
        status: 'pending',
        meeting_link: null,
        started_at: null,
        ended_at: null,
        duration_sec: null,
        created_at: '2026-08-11T09:00:00',
        updated_at: '2026-08-11T09:00:00',
      }),
    })
  })
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
