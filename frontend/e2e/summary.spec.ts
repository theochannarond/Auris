import { test, expect } from '@playwright/test'
import {
  MEETING_ID,
  mockMeetingsList,
  mockMeetingDetail,
  meetingListItem,
  meetingDetail,
  summary,
  mockRegister,
} from './fixtures/mockApi'


const OTHER_MEETING_ID = '66666666-6666-6666-6666-666666666666'

test.describe('Dashboard — historique', () => {
  test('chaque réunion est résumée sur sa carte', async ({ page }) => {
    await mockMeetingsList(page)
    await page.goto('/dashboard')

    await expect(page.getByRole('heading', { name: 'Historique de vos réunions' })).toBeVisible()
    await expect(page.getByText('Point trimestriel')).toBeVisible()
    await expect(page.getByText('11 août 2026')).toBeVisible()
    await expect(page.getByText('3 min 05 s')).toBeVisible()

    // Thème et ton viennent du compte rendu : c'est lui qu'on voit sur la carte
    await expect(page.getByText('📋 Suivi de projet')).toBeVisible()
    await expect(page.getByText('🎯 Formel')).toBeVisible()
  })

  test('une réunion sans compte rendu n\'affiche aucun badge', async ({ page }) => {
    await mockMeetingsList(page, [
      meetingListItem({ id: OTHER_MEETING_ID, title: 'Réunion non résumée', theme: null, tone: null }),
    ])
    await page.goto('/dashboard')

    await expect(page.getByText('Réunion non résumée')).toBeVisible()
    await expect(page.getByText(/^📋/)).toHaveCount(0)
    await expect(page.getByText(/^🎯/)).toHaveCount(0)
  })

  test('un historique vide invite à enregistrer', async ({ page }) => {
    await mockMeetingsList(page, [])
    await page.goto('/dashboard')

    await expect(page.getByText('Aucune réunion pour le moment')).toBeVisible()
    await expect(page.getByText('Vos réunions apparaîtront ici une fois enregistrées.')).toBeVisible()
  })
})

test.beforeEach(async ({ page }) => {
  await mockRegister(page)
})

test.describe('Dashboard — accès au compte rendu', () => {
  test('ouvrir une réunion affiche son compte rendu complet', async ({ page }) => {
    await mockMeetingsList(page)
    await mockMeetingDetail(page, meetingDetail({ summary: summary() }))

    await page.goto('/dashboard')
    await page.getByText('Point trimestriel').click()

    await expect(page).toHaveURL(new RegExp(`/meetings/${MEETING_ID}$`))
    await expect(page.getByRole('heading', { name: 'Compte rendu' })).toBeVisible()

    await expect(page.getByText("L'équipe a fait le point sur l'avancement du trimestre.")).toBeVisible()
    await expect(page.getByText('Décaler la livraison au 15 septembre')).toBeVisible()
    await expect(page.getByText('Marc rédige la note de cadrage')).toBeVisible()
    await expect(page.getByText('⚡ Généré en 3.1 s')).toBeVisible()
  })

  test('sans compte rendu, la génération est proposée', async ({ page }) => {
    await mockMeetingDetail(page, meetingDetail({ summary: null }))
    await page.goto(`/meetings/${MEETING_ID}`)

    await expect(
      page.getByText("Aucun compte rendu n'a encore été généré pour cette réunion.")
    ).toBeVisible()
    // Le bouton n'apparaît que si une transcription existe : sans texte, rien à résumer
    await expect(page.getByRole('button', { name: 'Générer le compte-rendu' })).toBeEnabled()
  })

  test('le retour ramène à l\'historique', async ({ page }) => {
    await mockMeetingsList(page)
    await mockMeetingDetail(page, meetingDetail({ summary: summary() }))

    await page.goto(`/meetings/${MEETING_ID}`)
    await page.getByRole('link', { name: '← Retour à l\'historique' }).click()

    await expect(page).toHaveURL(/\/dashboard$/)
    await expect(page.getByText('Point trimestriel')).toBeVisible()
  })
})

test.beforeEach(async ({ page }) => {
  await mockRegister(page)
})
