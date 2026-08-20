import { test, expect } from '@playwright/test'
import { mockKeycloakAuth, mockConsent, mockRegister } from './fixtures/mockApi'

test.describe('Connexion', () => {
  test('la page d\'accueil propose la connexion Keycloak', async ({ page }) => {
    await page.goto('/')

    await expect(page.getByRole('heading', { name: 'Auris' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Se connecter' })).toBeEnabled()
    await expect(page.getByText('Authentification sécurisée via Keycloak')).toBeVisible()
  })

  test('le bouton initie le flux OIDC avec les bons paramètres', async ({ page }) => {
    await mockKeycloakAuth(page)
    await page.goto('/')

    await page.getByRole('button', { name: 'Se connecter' }).click()
    await page.waitForURL(/openid-connect\/auth/)

    // Ce que l'application demande à Keycloak est vérifiable ; ce que Keycloak
    // répond ne l'est pas, faute de callback côté application (voir la PR).
    const params = new URL(page.url()).searchParams
    expect(params.get('client_id')).toBe('auris-frontend')
    expect(params.get('response_type')).toBe('code')
    expect(params.get('redirect_uri')).toBe('http://localhost:5173')
    expect(params.get('scope')).toContain('openid')
  })
})

test.describe('Consentement RGPD', () => {
  test('l\'écran détaille le traitement des données', async ({ page }) => {
    await page.goto('/consent')

    await expect(page.getByRole('heading', { name: 'Consentement RGPD' })).toBeVisible()
    await expect(page.getByText('Vos données restent hébergées en Union Européenne')).toBeVisible()
    await expect(page.getByText('Rétention maximale : 12 mois')).toBeVisible()
    await expect(page.getByText(/RGPD Art\. 7 et Art\. 9/)).toBeVisible()
  })

  test('la confirmation reste bloquée tant que la case n\'est pas cochée', async ({ page }) => {
    await page.goto('/consent')

    const confirm = page.getByRole('button', { name: 'Confirmer mon consentement' })
    await expect(confirm).toBeDisabled()

    await page.getByRole('checkbox').check()
    await expect(confirm).toBeEnabled()
  })

  test('confirmer enregistre le consentement puis mène au dictaphone', async ({ page }) => {
    await mockConsent(page)
    await page.goto('/consent')

    await page.getByRole('checkbox').check()

    const [request] = await Promise.all([
      page.waitForRequest(
        (r) => r.url().includes('/api/v1/consents') && r.method() === 'POST'
      ),
      page.getByRole('button', { name: 'Confirmer mon consentement' }).click(),
    ])

    // Le consentement doit être horodaté : c'est la preuve exigée par l'Art.7
    expect(request.postDataJSON()).toHaveProperty('given_at')
    await expect(page).toHaveURL(/\/dictaphone$/)
  })
})

test.beforeEach(async ({ page }) => {
  await mockRegister(page)
})
