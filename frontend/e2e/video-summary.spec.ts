import { test, expect } from '@playwright/test'
import {
  VIDEO_MEETING_ID,
  meetingListItem,
  mockMeetingsList,
  mockMeetingDetail,
  videoMeetingDetail,
  summary,
} from './fixtures/mockApi'

/**
 * Compte rendu d'une réunion vidéo, de l'historique à la page de détail.
 *
 * Réserve à connaître : rien ne distingue une réunion vidéo d'un dictaphone
 * sur les cartes du dashboard. MeetingCard reçoit bien `mode` dans ses données
 * mais ne l'affiche jamais — le mode n'apparaît que sur la page de détail.
 */

const VIDEO_CARD = meetingListItem({
  id:           VIDEO_MEETING_ID,
  title:        'Comité de pilotage',
  mode:         'video',
  duration_sec: 2730,
  created_at:   '2026-08-12T14:00:00',
  theme:        'Gouvernance projet',
  tone:         'formal',
})

const VIDEO_SUMMARY = summary({
  content:      'Le comité a validé la feuille de route du second semestre.',
  decisions:    ['Valider le budget du lot 3', 'Reporter la refonte du portail au T1'],
  action_items: ['Sophie diffuse le relevé de décisions', 'Marc chiffre la reprise du lot 3'],
  theme:        'Gouvernance projet',
  processing_ms: 5600,
})

test.describe('Réunion vidéo — compte rendu', () => {
  test('la réunion vidéo figure dans l\'historique avec sa classification', async ({ page }) => {
    await mockMeetingsList(page, [VIDEO_CARD])
    await page.goto('/dashboard')

    await expect(page.getByText('Comité de pilotage')).toBeVisible()
    await expect(page.getByText('12 août 2026')).toBeVisible()
    await expect(page.getByText('45 min 30 s')).toBeVisible()

    await expect(page.getByText('📋 Gouvernance projet')).toBeVisible()
    await expect(page.getByText('🎯 Formel')).toBeVisible()
  })

  test('dictaphone et vidéo se côtoient dans le même historique', async ({ page }) => {
    await mockMeetingsList(page, [VIDEO_CARD, meetingListItem()])
    await page.goto('/dashboard')

    // Les deux cartes sont rendues à l'identique : seul le titre permet de
    // savoir laquelle a été captée par le bot. Signalé en revue.
    await expect(page.getByText('Comité de pilotage')).toBeVisible()
    await expect(page.getByText('Point trimestriel')).toBeVisible()
  })

  test('ouvrir la réunion vidéo mène à son compte rendu', async ({ page }) => {
    await mockMeetingsList(page, [VIDEO_CARD])
    await mockMeetingDetail(page, videoMeetingDetail({ summary: VIDEO_SUMMARY }))

    await page.goto('/dashboard')
    await page.getByText('Comité de pilotage').click()

    await expect(page).toHaveURL(new RegExp(`/meetings/${VIDEO_MEETING_ID}$`))
    await expect(page.getByRole('heading', { name: 'Compte rendu' })).toBeVisible()
    await expect(page.getByText('Réunion en ligne')).toBeVisible()

    await expect(
      page.getByText('Le comité a validé la feuille de route du second semestre.')
    ).toBeVisible()
    await expect(page.getByText('⚡ Généré en 5.6 s')).toBeVisible()
  })

  test('les décisions et les actions du comité sont restituées', async ({ page }) => {
    await mockMeetingDetail(page, videoMeetingDetail({ summary: VIDEO_SUMMARY }))
    await page.goto(`/meetings/${VIDEO_MEETING_ID}`)

    await expect(page.getByRole('heading', { name: '✓ Décisions prises' })).toBeVisible()
    await expect(page.getByText('Valider le budget du lot 3')).toBeVisible()
    await expect(page.getByText('Reporter la refonte du portail au T1')).toBeVisible()

    await expect(page.getByRole('heading', { name: '→ Actions à réaliser' })).toBeVisible()
    await expect(page.getByText('Sophie diffuse le relevé de décisions')).toBeVisible()
    await expect(page.getByText('Marc chiffre la reprise du lot 3')).toBeVisible()

    // Rien de plus que ce qui a été renvoyé : deux décisions, deux actions
    await expect(page.getByRole('listitem')).toHaveCount(4)
  })

  test('une réunion vidéo sans compte rendu propose de le générer', async ({ page }) => {
    await mockMeetingDetail(page, videoMeetingDetail({ summary: null }))
    await page.goto(`/meetings/${VIDEO_MEETING_ID}`)

    await expect(
      page.getByText("Aucun compte rendu n'a encore été généré pour cette réunion.")
    ).toBeVisible()

    // Le bot a livré sa transcription : il y a de quoi résumer
    await expect(page.getByRole('button', { name: 'Générer le compte-rendu' })).toBeEnabled()
  })
})
