import { test, expect } from '@playwright/test'
import {
  MEETING_LINK,
  VIDEO_MEETING_ID,
  mockCreateVideoMeeting,
  mockCreateVideoMeetingFailure,
  mockMeetingStatus,
} from './fixtures/mockApi'

/**
 * Lancement d'une réunion vidéo.
 *
 * Auris ne crée aucune salle : l'utilisateur colle le lien d'une réunion
 * existante (Meet, Teams, Zoom) et le backend y dépêche un bot Vexa. Ce qui
 * est vérifié ici s'arrête donc au navigateur — que le lien saisi parte bien
 * au serveur, et que l'écran de suivi prenne le relais. Ni le backend ni Vexa
 * ne tournent pendant ces tests.
 */

const TITLE = 'Comité de pilotage'

test.describe('Réunion vidéo — lancement', () => {
  test('la page présente le formulaire de lancement', async ({ page }) => {
    await page.goto('/video')

    await expect(page.getByRole('heading', { name: 'Mode réunion vidéo' })).toBeVisible()
    await expect(page.getByPlaceholder('Titre de la réunion')).toHaveValue('')
    await expect(page.getByPlaceholder('Lien Google Meet / Teams / Zoom')).toHaveValue('')
    await expect(page.getByRole('button', { name: 'Lancer la réunion' })).toBeEnabled()
  })

  test('un formulaire incomplet n\'envoie rien au serveur', async ({ page }) => {
    await mockCreateVideoMeeting(page)
    await page.goto('/video')

    // Un bot dépêché sans lien exploitable resterait à tourner dans le vide :
    // on vérifie que la requête ne part pas du tout, pas seulement que
    // l'utilisateur est averti
    const creations: string[] = []
    page.on('request', (request) => {
      if (request.method() === 'POST' && request.url().includes('/meetings/video')) {
        creations.push(request.url())
      }
    })

    const launch = page.getByRole('button', { name: 'Lancer la réunion' })
    const error  = page.getByText('Le titre et le lien de la réunion sont obligatoires.')

    await launch.click()
    await expect(error).toBeVisible()

    // Le titre seul ne suffit pas : c'est le lien qui désigne la réunion
    await page.getByPlaceholder('Titre de la réunion').fill(TITLE)
    await launch.click()
    await expect(error).toBeVisible()

    expect(creations).toHaveLength(0)
  })

  test('lancer la réunion transmet le titre et le lien saisis', async ({ page }) => {
    await mockCreateVideoMeeting(page)
    await mockMeetingStatus(page, ['pending'])
    await page.goto('/video')

    await page.getByPlaceholder('Titre de la réunion').fill(TITLE)
    await page.getByPlaceholder('Lien Google Meet / Teams / Zoom').fill(MEETING_LINK)

    const [request] = await Promise.all([
      page.waitForRequest(
        (r) => r.url().includes('/api/v1/meetings/video') && r.method() === 'POST'
      ),
      page.getByRole('button', { name: 'Lancer la réunion' }).click(),
    ])

    // C'est ce lien que le backend passe à Vexa pour y envoyer le bot :
    // s'il arrivait déformé, le bot ne rejoindrait jamais rien
    expect(request.postDataJSON()).toEqual({
      title:        TITLE,
      meeting_link: MEETING_LINK,
    })
  })

  test('la réunion créée laisse place au suivi du bot', async ({ page }) => {
    await mockCreateVideoMeeting(page)
    await mockMeetingStatus(page, ['pending'])
    await page.goto('/video')

    await page.getByPlaceholder('Titre de la réunion').fill(TITLE)
    await page.getByPlaceholder('Lien Google Meet / Teams / Zoom').fill(MEETING_LINK)
    await page.getByRole('button', { name: 'Lancer la réunion' }).click()

    // Le formulaire disparaît : la même réunion ne peut pas être lancée deux fois
    await expect(page.getByPlaceholder('Titre de la réunion')).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Lancer la réunion' })).toHaveCount(0)

    // L'identifiant renvoyé est celui que le suivi va sonder
    await expect(page.getByText(`ID réunion : ${VIDEO_MEETING_ID}`)).toBeVisible()
  })

  test('un échec serveur laisse le formulaire en place', async ({ page }) => {
    await mockCreateVideoMeetingFailure(page)
    await page.goto('/video')

    await page.getByPlaceholder('Titre de la réunion').fill(TITLE)
    await page.getByPlaceholder('Lien Google Meet / Teams / Zoom').fill(MEETING_LINK)
    await page.getByRole('button', { name: 'Lancer la réunion' }).click()

    await expect(page.getByText('Une erreur est survenue. Veuillez réessayer.')).toBeVisible()

    // La saisie n'est pas perdue : réessayer ne demande pas de recoller le lien
    await expect(page.getByPlaceholder('Lien Google Meet / Teams / Zoom')).toHaveValue(MEETING_LINK)
  })
})
