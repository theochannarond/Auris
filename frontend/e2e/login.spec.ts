import { test, expect } from '@playwright/test'
import { mockKeycloakAuth } from './fixtures/mockApi'

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

    const params = new URL(page.url()).searchParams
    expect(params.get('client_id')).toBe('auris-frontend')
    expect(params.get('response_type')).toBe('code')
    expect(params.get('redirect_uri')).toBe('http://localhost:5173')
    expect(params.get('scope')).toContain('openid')
  })
})