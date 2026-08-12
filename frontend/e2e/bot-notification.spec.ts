import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import {
  MEETING_LINK,
  mockCreateVideoMeeting,
  mockMeetingStatus,
} from './fixtures/mockApi'

/**
 * Notification d'arrivée du bot dans la réunion.
 *
 * L'utilisateur ne voit pas le bot rejoindre : il ne dispose que de cette
 * notification, alimentée par le sondage de useMeetingStatus. C'est donc le
 * seul retour dont il dispose pour savoir si sa réunion est bien captée.
 *
 * Le sondage tourne à 3 s (valeur par défaut du hook, laissée telle quelle par
 * VideoModePage) : les basculements attendus ici coûtent un délai réel, d'où
 * les temporisations explicites plutôt que le délai par défaut de 5 s.
 */

const TITLE = 'Comité de pilotage'

// Le message de la page et celui de la notification se ressemblent au point de
// se contenir l'un l'autre : les libellés exacts évitent une correspondance double.
const WAITING_ON_PAGE  = 'En attente que le bot rejoigne...'
const WAITING_NOTICE   = '⏳ En attente que le bot rejoigne la réunion...'
const JOINED_ON_PAGE   = '✓ Le bot Auris a rejoint votre réunion'
const JOINED_NOTICE    = '✓ Le bot Auris a rejoint la réunion — enregistrement en cours'
const FAILED_NOTICE    = "✗ Le bot n'a pas pu rejoindre la réunion. Vérifiez le lien et réessayez."

async function launchMeeting(page: Page) {
  await page.goto('/video')
  await page.getByPlaceholder('Titre de la réunion').fill(TITLE)
  await page.getByPlaceholder('Lien Google Meet / Teams / Zoom').fill(MEETING_LINK)
  await page.getByRole('button', { name: 'Lancer la réunion' }).click()
}

test.describe('Réunion vidéo — arrivée du bot', () => {
  test('tant que le bot n\'a pas rejoint, l\'attente est annoncée', async ({ page }) => {
    await mockCreateVideoMeeting(page)
    await mockMeetingStatus(page, ['pending'])
    await launchMeeting(page)

    await expect(page.getByText(WAITING_NOTICE)).toBeVisible()

    // Ce libellé-ci n'apparaît que sur un statut « pending » réellement reçu :
    // la notification, elle, affiche déjà l'attente avant le premier sondage
    await expect(page.getByText(WAITING_ON_PAGE, { exact: true })).toBeVisible()
  })

  test('le bot qui rejoint fait basculer la notification', async ({ page }) => {
    await mockCreateVideoMeeting(page)
    await mockMeetingStatus(page, ['pending', 'recording'])
    await launchMeeting(page)

    await expect(page.getByText(WAITING_NOTICE)).toBeVisible()

    // Le second sondage intervient une interrogation plus tard, soit ~3 s
    await expect(page.getByText(JOINED_NOTICE)).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText(JOINED_ON_PAGE)).toBeVisible()

    // L'attente disparaît : les deux messages ne cohabitent pas
    await expect(page.getByText(WAITING_NOTICE)).toHaveCount(0)
    await expect(page.getByText(WAITING_ON_PAGE, { exact: true })).toHaveCount(0)
  })

  test('un bot qui n\'a pas pu rejoindre indique la marche à suivre', async ({ page }) => {
    await mockCreateVideoMeeting(page)
    await mockMeetingStatus(page, ['failed'])
    await launchMeeting(page)

    // Le lien est la cause la plus probable, et la seule que l'utilisateur
    // puisse corriger lui-même : le message doit le dire
    await expect(page.getByText(FAILED_NOTICE)).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText(WAITING_NOTICE)).toHaveCount(0)
  })

  test('le sondage cesse une fois le bot arrivé', async ({ page }) => {
    await mockCreateVideoMeeting(page)
    await mockMeetingStatus(page, ['pending', 'recording'])

    let polls = 0
    page.on('request', (request) => {
      if (/\/api\/v1\/meetings\/[^/]+\/status/.test(request.url())) polls += 1
    })

    await launchMeeting(page)
    await expect(page.getByText(JOINED_NOTICE)).toBeVisible({ timeout: 10_000 })

    const afterJoin = polls

    // Une page de réunion reste ouverte des heures : un intervalle laissé armé
    // interrogerait le serveur jusqu'à la fermeture de l'onglet. On attend plus
    // qu'un cycle complet pour s'assurer qu'il a bien été désarmé.
    await page.waitForTimeout(4_000)
    expect(polls).toBe(afterJoin)
  })

  test('une fois l\'enregistrement terminé, aucune notification ne subsiste', async ({ page }) => {
    await mockCreateVideoMeeting(page)
    await mockMeetingStatus(page, ['processing'])
    await launchMeeting(page)

    // BotStatusNotification ne couvre que le sort du bot : le traitement qui
    // suit ne le concerne plus. L'écran devient alors muet — signalé en revue.
    await expect(page.getByText(WAITING_NOTICE)).toHaveCount(0)
    await expect(page.getByText(JOINED_NOTICE)).toHaveCount(0)
    await expect(page.getByText(FAILED_NOTICE)).toHaveCount(0)
  })
})
