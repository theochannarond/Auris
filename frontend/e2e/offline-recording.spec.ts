import { test, expect } from '@playwright/test'
import { mockCreateMeeting, mockRegister } from './fixtures/mockApi'

/**
 * Ces tests simulent une coupure réseau pendant l'enregistrement.
 * Playwright expose page.context().setOffline() pour couper le réseau
 * sans toucher au MediaRecorder — l'audio continue d'être capturé localement.
 */

const timer = /^\d{2}:\d{2}$/

test.describe('Dictaphone — mode hors ligne', () => {

  test('le banner offline s\'affiche quand la connexion est perdue', async ({ page }) => {
    await mockCreateMeeting(page)
    await page.goto('/dictaphone')

    await page.getByRole('button', { name: 'Enregistrer' }).click()
    await expect(page.getByText('Enregistrement en cours...')).toBeVisible()

    // Simule la coupure réseau
    await page.context().setOffline(true)

    await expect(page.locator('.fixed').getByText(/Connexion perdue/)).toBeVisible({ timeout: 3000 })
  })

  test('l\'enregistrement continue après une coupure réseau', async ({ page }) => {
    await mockCreateMeeting(page)
    await page.goto('/dictaphone')

    await page.getByRole('button', { name: 'Enregistrer' }).click()
    await expect(page.getByText(timer)).not.toHaveText('00:00', { timeout: 5000 })

    // Coupe le réseau
    await page.context().setOffline(true)

    await expect(page.locator('.fixed').getByText(/Connexion perdue/)).toBeVisible({ timeout: 3000 })

    // Le chronomètre continue de tourner — l'enregistrement n'est pas interrompu
    const timeBefore = await page.getByText(timer).textContent()
    await page.waitForTimeout(2000)
    const timeAfter = await page.getByText(timer).textContent()

    expect(timeBefore).not.toBe(timeAfter)
    await expect(page.getByText('Enregistrement en cours...')).toBeVisible()
  })

  test('le banner de reconnexion s\'affiche quand la connexion revient', async ({ page }) => {
    await mockCreateMeeting(page)
    await page.goto('/dictaphone')

    await page.getByRole('button', { name: 'Enregistrer' }).click()
    await expect(page.getByText('Enregistrement en cours...')).toBeVisible()

    // Coupe puis rétablit la connexion
    await page.context().setOffline(true)
    await expect(page.locator('.fixed').getByText(/Connexion perdue/)).toBeVisible({ timeout: 3000 })

    await page.context().setOffline(false)
    await expect(page.locator('.fixed').getByText(/Connexion rétablie/)).toBeVisible({ timeout: 3000 })
  })

  test('arrêter après reconnexion produit un enregistrement valide', async ({ page }) => {
    await mockCreateMeeting(page)
    await page.goto('/dictaphone')

    await page.getByRole('button', { name: 'Enregistrer' }).click()
    await expect(page.getByText(timer)).not.toHaveText('00:00', { timeout: 5000 })

    // Simule coupure puis reconnexion
    await page.context().setOffline(true)
    await page.waitForTimeout(1000)
    await page.context().setOffline(false)

    await page.waitForTimeout(500)

    // L'enregistrement peut être arrêté normalement
    await page.getByRole('button', { name: 'Arrêter' }).click()

    await expect(page.getByText('Enregistrement terminé')).toBeVisible()
    await expect(page.locator('audio')).toHaveAttribute('src', /^blob:/)
    await expect(page.getByRole('button', { name: 'Envoyer pour transcription' })).toBeEnabled()
  })
})

test.beforeEach(async ({ page }) => {
  await mockRegister(page)
})