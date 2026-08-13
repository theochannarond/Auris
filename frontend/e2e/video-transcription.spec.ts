import { test, expect } from '@playwright/test'
import {
  VIDEO_MEETING_ID,
  VIDEO_TRANSCRIPTION_TEXT,
  TRANSCRIPTION_ID,
  mockMeetingDetail,
  videoMeetingDetail,
} from './fixtures/mockApi'

/**
 * Transcription d'une réunion vidéo.
 *
 * Le parcours de Sophie et celui de Marc convergent sur la même page de
 * détail : ce qui est vérifié ici, ce sont les différences propres à la
 * vidéo — le mode annoncé, et une diarisation qui porte des noms de
 * participants plutôt que des locuteurs anonymes.
 */

test.describe('Réunion vidéo — transcription', () => {
  test('la réunion est identifiée comme une réunion en ligne', async ({ page }) => {
    await mockMeetingDetail(page, videoMeetingDetail())
    await page.goto(`/meetings/${VIDEO_MEETING_ID}`)

    await expect(page.getByRole('heading', { name: 'Comité de pilotage' })).toBeVisible()

    // Seul endroit de l'application où le mode est visible : les cartes du
    // dashboard ne le montrent pas
    await expect(page.getByText('Réunion en ligne')).toBeVisible()
    await expect(page.getByText('45 min 30 s')).toBeVisible()
  })

  test('le texte capté par le bot est affiché', async ({ page }) => {
    await mockMeetingDetail(page, videoMeetingDetail())
    await page.goto(`/meetings/${VIDEO_MEETING_ID}`)

    await expect(page.getByRole('heading', { name: 'Transcription' })).toBeVisible()
    await expect(page.getByText(VIDEO_TRANSCRIPTION_TEXT)).toBeVisible()
  })

  test('chaque participant est nommé dans la prise de parole', async ({ page }) => {
    await mockMeetingDetail(page, videoMeetingDetail())
    await page.goto(`/meetings/${VIDEO_MEETING_ID}`)

    await expect(page.getByRole('heading', { name: 'Prise de parole' })).toBeVisible()

    // Une entrée de légende, plus un en-tête par prise de parole : Sophie
    // intervient deux fois, Marc une seule
    await expect(page.getByText('Sophie Marchand')).toHaveCount(3)
    await expect(page.getByText('Marc Lefèvre')).toHaveCount(2)

    await expect(page.getByText('Le chantier de migration est terminé.')).toBeVisible()
    await expect(page.getByText('00:45 — 01:32')).toBeVisible()
  })

  test('une réunion à nombreux participants reste lisible', async ({ page }) => {
    // Une visioconférence réunit couramment plus de monde qu'un dictaphone.
    // La palette de DiarizationDisplay compte six teintes et boucle au-delà :
    // le septième participant partage la couleur du premier, et seul son nom
    // permet encore de les distinguer.
    const participants = [
      'Sophie Marchand', 'Marc Lefèvre', 'Inès Bouchard', 'Yann Deschamps',
      'Clara Nguyen', 'Tarek Amrani', 'Julie Vasseur',
    ]

    await mockMeetingDetail(
      page,
      videoMeetingDetail({
        transcription: {
          id:            TRANSCRIPTION_ID,
          status:        'completed',
          raw_text:      VIDEO_TRANSCRIPTION_TEXT,
          // Le texte ne reprend pas le nom du locuteur : sans cela il compterait
          // comme une occurrence de plus et le décompte ci-dessous ne dirait rien
          diarization: participants.map((speaker, index) => ({
            speaker,
            start: index * 60,
            end:   index * 60 + 55,
            text:  `Avancement du lot ${index + 1}.`,
          })),
          language:      'fr',
          processing_ms: 8400,
        },
      })
    )
    await page.goto(`/meetings/${VIDEO_MEETING_ID}`)

    // Une entrée de légende et un en-tête de segment pour chacun
    for (const speaker of participants) {
      await expect(page.getByText(speaker)).toHaveCount(2)
    }

    // Le dernier segment est bien rendu, malgré la couleur réemployée
    await expect(page.getByText('Avancement du lot 7.')).toBeVisible()
    await expect(page.getByText('06:00 — 06:55')).toBeVisible()
  })

  test('un enregistrement encore en traitement n\'affiche aucune prise de parole', async ({ page }) => {
    await mockMeetingDetail(
      page,
      videoMeetingDetail({
        transcription: {
          id:            TRANSCRIPTION_ID,
          status:        'processing',
          raw_text:      null,
          diarization:   null,
          language:      null,
          processing_ms: null,
        },
      })
    )
    await page.goto(`/meetings/${VIDEO_MEETING_ID}`)

    await expect(page.getByText('La transcription est en cours de traitement.')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Prise de parole' })).toHaveCount(0)

    // La réunion reste consultable et correctement étiquetée entre-temps
    await expect(page.getByText('Réunion en ligne')).toBeVisible()
  })
})
