import { test, expect } from '@playwright/test'

/**
 * Vérifie le harnais lui-même, pas l'application : serveur Vite démarré,
 * bundle servi, React monté. Si ce test tombe, aucun autre n'a de sens.
 */
test('le serveur de dev répond et React monte l\'application', async ({ page }) => {
  const response = await page.goto('/')

  expect(response?.status()).toBe(200)
  await expect(page.locator('#root')).not.toBeEmpty()
})
