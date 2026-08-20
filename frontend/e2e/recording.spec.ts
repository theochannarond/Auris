import { test, expect } from '@playwright/test'
import { mockCreateMeeting, mockRegister } from './fixtures/mockApi'


/**
 * Le micro est un périphérique synthétique fourni par Chromium
 * (--use-fake-device-for-media-stream, voir playwright.config.ts) : le
 * MediaRecorder tourne donc pour de vrai, sur un flux audio généré.
 */

// Le chronomètre est le seul élément au format MM:SS strict de la page
const timer = /^\d{2}:\d{2}$/

test.describe('Dictaphone — enregistrement', () => {
  test('la page s\'ouvre prête à enregistrer', async ({ page }) => {
    await page.goto('/dictaphone')

    await expect(page.getByRole('heading', { name: 'Mode dictaphone' })).toBeVisible()
    await expect(page.getByText('Prêt à enregistrer')).toBeVisible()
    await expect(page.getByText(timer)).toHaveText('00:00')
    await expect(page.getByRole('button', { name: 'Enregistrer' })).toBeEnabled()
  })

  test('démarrer crée la réunion puis lance la capture', async ({ page }) => {
    await mockCreateMeeting(page)
    await page.goto('/dictaphone')

    const [request] = await Promise.all([
      page.waitForRequest(
        (r) => r.url().includes('/api/v1/meetings') && r.method() === 'POST'
      ),
      page.getByRole('button', { name: 'Enregistrer' }).click(),
    ])

    // La réunion est créée avant la capture : sans son id, l'audio n'aurait
    // nulle part où être envoyé
    expect(request.postDataJSON()).toHaveProperty('title')

    await expect(page.getByText('Enregistrement en cours...')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Pause' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Arrêter' })).toBeVisible()

    // Le chronomètre quitte 00:00 : la capture tourne réellement
    await expect(page.getByText(timer)).not.toHaveText('00:00', { timeout: 5000 })
  })

  test('mettre en pause puis reprendre l\'enregistrement', async ({ page }) => {
    await mockCreateMeeting(page)
    await page.goto('/dictaphone')
    await page.getByRole('button', { name: 'Enregistrer' }).click()
    await expect(page.getByText('Enregistrement en cours...')).toBeVisible()

    await page.getByRole('button', { name: 'Pause' }).click()
    await expect(page.getByText('En pause')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Reprendre' })).toBeVisible()

    await page.getByRole('button', { name: 'Reprendre' }).click()
    await expect(page.getByText('Enregistrement en cours...')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Pause' })).toBeVisible()
  })

  test('arrêter produit un enregistrement écoutable', async ({ page }) => {
    await mockCreateMeeting(page)
    await page.goto('/dictaphone')
    await page.getByRole('button', { name: 'Enregistrer' }).click()
    await expect(page.getByText('Enregistrement en cours...')).toBeVisible()

    // MediaRecorder est démarré avec un découpage à la seconde : on lui laisse
    // le temps de produire au moins un fragment avant l'arrêt
    await expect(page.getByText(timer)).not.toHaveText('00:00', { timeout: 5000 })

    await page.getByRole('button', { name: 'Arrêter' }).click()

    await expect(page.getByText('Enregistrement terminé')).toBeVisible()
    await expect(page.getByText('Aperçu de votre enregistrement')).toBeVisible()
    await expect(page.locator('audio')).toHaveAttribute('src', /^blob:/)
    await expect(page.getByRole('button', { name: 'Envoyer pour transcription' })).toBeEnabled()
  })
})

test.beforeEach(async ({ page }) => {
  await mockRegister(page)
})