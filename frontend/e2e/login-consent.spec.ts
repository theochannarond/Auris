import { test, expect } from '@playwright/test'
import { mockConsent, mockRegister } from './fixtures/mockApi'

test.describe('Consentement RGPD', () => {
  test.beforeEach(async ({ page }) => {
    await mockRegister(page)
  })

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

    expect(request.postDataJSON()).toHaveProperty('given_at')
    await expect(page).toHaveURL(/\/dictaphone$/)
  })
})