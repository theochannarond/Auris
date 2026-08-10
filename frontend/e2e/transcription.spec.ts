import { test, expect } from '@playwright/test'
import {
  MEETING_ID,
  TRANSCRIPTION_TEXT,
  mockCreateMeeting,
  mockAudioUpload,
  mockTranscriptionStart,
  mockTranscriptionStatus,
  mockMeetingDetail,
  meetingDetail,
} from './fixtures/mockApi'

const timer = /^\d{2}:\d{2}$/

test.describe('Transcription — suivi du traitement', () => {
  test('l\'envoi affiche la progression puis la fin du traitement', async ({ page }) => {
    await mockCreateMeeting(page)
    await mockAudioUpload(page)
    await mockTranscriptionStart(page)
    // Premier sondage en cours de traitement, les suivants terminés
    await mockTranscriptionStatus(page, ['processing', 'completed'])

    await page.goto('/dictaphone')
    await page.getByRole('button', { name: 'Enregistrer' }).click()
    await expect(page.getByText(timer)).not.toHaveText('00:00', { timeout: 5000 })
    await page.getByRole('button', { name: 'Arrêter' }).click()

    await page.getByRole('button', { name: 'Envoyer pour transcription' }).click()

    await expect(page.getByText('✓ Enregistrement envoyé avec succès')).toBeVisible()
    await expect(
      page.getByText('Transcription de votre enregistrement en cours...')
    ).toBeVisible()

    // Le hook sonde toutes les 3 s : on laisse passer au moins un cycle
    await expect(page.getByText('✓ Transcription terminée')).toBeVisible({ timeout: 15000 })
    await expect(page.getByText('Traitée en 4.2 s')).toBeVisible()
  })

  test('un échec de transcription est signalé à l\'utilisateur', async ({ page }) => {
    await mockCreateMeeting(page)
    await mockAudioUpload(page)
    await mockTranscriptionStart(page)
    await mockTranscriptionStatus(page, ['failed'])

    await page.goto('/dictaphone')
    await page.getByRole('button', { name: 'Enregistrer' }).click()
    await expect(page.getByText(timer)).not.toHaveText('00:00', { timeout: 5000 })
    await page.getByRole('button', { name: 'Arrêter' }).click()
    await page.getByRole('button', { name: 'Envoyer pour transcription' }).click()

    await expect(page.getByText('✗ La transcription a échoué.')).toBeVisible()
  })
})

test.describe('Transcription — affichage sur la réunion', () => {
  test('le texte transcrit est affiché après traitement', async ({ page }) => {
    await mockMeetingDetail(page)
    await page.goto(`/meetings/${MEETING_ID}`)

    await expect(page.getByRole('heading', { name: 'Transcription' })).toBeVisible()
    await expect(page.getByText(TRANSCRIPTION_TEXT)).toBeVisible()
  })

  test('la prise de parole est ventilée par locuteur', async ({ page }) => {
    await mockMeetingDetail(page)
    await page.goto(`/meetings/${MEETING_ID}`)

    await expect(page.getByRole('heading', { name: 'Prise de parole' })).toBeVisible()
    await expect(page.getByText('Le trimestre est en avance.')).toBeVisible()
    // Chaque locuteur apparaît dans la légende et sur son segment
    await expect(page.getByText('Locuteur 1')).toHaveCount(2)
    await expect(page.getByText('Locuteur 2')).toHaveCount(2)
    await expect(page.getByText('00:12 — 00:30')).toBeVisible()
  })

  test('une transcription encore en cours ne montre pas de texte', async ({ page }) => {
    await mockMeetingDetail(
      page,
      meetingDetail({
        transcription: {
          id: 'in-progress',
          status: 'processing',
          raw_text: null,
          diarization: null,
          language: null,
          processing_ms: null,
        },
      })
    )
    await page.goto(`/meetings/${MEETING_ID}`)

    await expect(page.getByText('La transcription est en cours de traitement.')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Prise de parole' })).toHaveCount(0)
  })
})
