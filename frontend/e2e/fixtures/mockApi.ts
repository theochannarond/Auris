import type { Page } from '@playwright/test'

/**
 * Simulacres réseau pour les tests E2E.
 *
 * Ni le backend, ni Keycloak, ni les API externes ne tournent pendant ces
 * tests : chaque appel est intercepté et servi par une réponse figée. Ce qui
 * est validé ici, c'est le comportement du navigateur — routage, composants,
 * enchaînement des états — pas la chaîne de traitement réelle.
 */

/**
 * Serveur d'autorisation Keycloak.
 *
 * On répond une page factice pour que la redirection aboutisse : l'URL
 * demandée reste ainsi inspectable, ce qui permet de vérifier que
 * l'application initie correctement le flux OIDC.
 */
export async function mockKeycloakAuth(page: Page) {
  await page.route('**/protocol/openid-connect/auth*', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'text/html',
      body: '<html><body><h1>Keycloak</h1></body></html>',
    })
  )
}

export const MEETING_ID = '22222222-2222-2222-2222-222222222222'

/**
 * Création d'une réunion (dictaphone).
 *
 * Le motif attrape aussi le GET du dashboard : on rend la main via fallback()
 * pour tout ce qui n'est pas un POST, afin de ne pas court-circuiter les
 * autres interceptions enregistrées par le test.
 */
export async function mockCreateMeeting(page: Page) {
  await page.route('**/api/v1/meetings', (route) => {
    if (route.request().method() !== 'POST') return route.fallback()

    return route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({
        id: MEETING_ID,
        owner_id: '33333333-3333-3333-3333-333333333333',
        title: 'Réunion du 11/08/2026',
        mode: 'dictaphone',
        status: 'pending',
        meeting_link: null,
        started_at: null,
        ended_at: null,
        duration_sec: null,
        created_at: '2026-08-11T09:00:00',
        updated_at: '2026-08-11T09:00:00',
      }),
    })
  })
}

export const TRANSCRIPTION_ID = '44444444-4444-4444-4444-444444444444'

/** Upload de l'audio et passage de la réunion en "processing". */
export async function mockAudioUpload(page: Page) {
  await page.route('**/api/v1/meetings/*/audio', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ id: MEETING_ID, status: 'pending' }),
    })
  )

  await page.route('**/api/v1/meetings/*/status', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ id: MEETING_ID, status: 'processing' }),
    })
  )
}

/** Lancement de la transcription. */
export async function mockTranscriptionStart(page: Page) {
  await page.route('**/api/v1/transcriptions', (route) =>
    route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({ id: TRANSCRIPTION_ID, meeting_id: MEETING_ID, status: 'processing' }),
    })
  )
}

/**
 * Polling du statut de transcription.
 *
 * Consomme la liste fournie appel après appel, puis reste sur la dernière
 * valeur : c'est ce qui permet de rejouer une vraie progression
 * processing → completed sans dépendre du nombre exact de sondages.
 */
export async function mockTranscriptionStatus(page: Page, sequence: string[]) {
  let call = 0

  await page.route('**/api/v1/transcriptions/*/status', (route) => {
    const status = sequence[Math.min(call, sequence.length - 1)]
    call += 1

    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: TRANSCRIPTION_ID,
        meeting_id: MEETING_ID,
        status,
        processing_ms: status === 'completed' ? 4200 : null,
        error_message: null,
      }),
    })
  })
}

// ─── Mode vidéo ───

export const VIDEO_MEETING_ID = '77777777-7777-7777-7777-777777777777'
export const MEETING_LINK     = 'https://meet.google.com/abc-defg-hij'

/**
 * Création d'une réunion vidéo — POST /api/v1/meetings/video.
 *
 * Le chemin porte un segment de plus que celui du dictaphone : le motif de
 * mockCreateMeeting, qui s'arrête à « meetings », ne l'attrape pas.
 *
 * Le titre et le lien reçus sont renvoyés tels quels, comme le fait le
 * backend : le test n'a pas à connaître d'avance ce qu'il a saisi.
 */
export async function mockCreateVideoMeeting(page: Page) {
  await page.route('**/api/v1/meetings/video', (route) => {
    if (route.request().method() !== 'POST') return route.fallback()

    const sent = route.request().postDataJSON() ?? {}

    return route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({
        id: VIDEO_MEETING_ID,
        owner_id: '33333333-3333-3333-3333-333333333333',
        title: sent.title,
        mode: 'video',
        status: 'pending',
        meeting_link: sent.meeting_link,
        started_at: null,
        ended_at: null,
        duration_sec: null,
        created_at: '2026-08-12T09:00:00',
        updated_at: '2026-08-12T09:00:00',
      }),
    })
  })
}

/** Échec de la création côté serveur, pour vérifier le message d'erreur. */
export async function mockCreateVideoMeetingFailure(page: Page) {
  await page.route('**/api/v1/meetings/video', (route) => {
    if (route.request().method() !== 'POST') return route.fallback()

    return route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Erreur interne' }),
    })
  })
}

/**
 * Sondage du statut d'une réunion — GET /api/v1/meetings/{id}/status.
 *
 * Même principe que mockTranscriptionStatus : la liste est consommée appel
 * après appel, puis la dernière valeur est répétée. useMeetingStatus interroge
 * toutes les 3 s et cesse dès le premier statut final, ce qui rend le nombre
 * de sondages imprévisible — d'où cette séquence plutôt qu'un compteur exact.
 *
 * Attention : mockAudioUpload pose une interception sur le même motif. Si les
 * deux sont enregistrées, Playwright retient la dernière posée.
 */
export async function mockMeetingStatus(page: Page, sequence: string[]) {
  let call = 0

  await page.route('**/api/v1/meetings/*/status', (route) => {
    const status = sequence[Math.min(call, sequence.length - 1)]
    call += 1

    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ id: VIDEO_MEETING_ID, status }),
    })
  })
}

/** Réunion telle qu'affichée sur une carte du dashboard. */
export function meetingListItem(overrides: Record<string, unknown> = {}) {
  return {
    id: MEETING_ID,
    title: 'Point trimestriel',
    mode: 'dictaphone',
    status: 'completed',
    duration_sec: 185,
    created_at: '2026-08-11T09:00:00',
    theme: 'Suivi de projet',
    tone: 'formal',
    ...overrides,
  }
}

/** Historique des réunions — GET /api/v1/meetings. */
export async function mockMeetingsList(page: Page, items = [meetingListItem()]) {
  await page.route('**/api/v1/meetings', (route) => {
    if (route.request().method() !== 'GET') return route.fallback()

    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(items),
    })
  })
}

/** Compte rendu généré par Mistral. */
export function summary(overrides: Record<string, unknown> = {}) {
  return {
    id: '55555555-5555-5555-5555-555555555555',
    content: "L'équipe a fait le point sur l'avancement du trimestre.",
    decisions: ['Décaler la livraison au 15 septembre'],
    action_items: ['Marc rédige la note de cadrage'],
    tone: 'formal',
    theme: 'Suivi de projet',
    processing_ms: 3100,
    created_at: '2026-08-11T09:05:00',
    ...overrides,
  }
}

export const TRANSCRIPTION_TEXT =
  'Bonjour à tous. Nous ouvrons la réunion sur le suivi du trimestre.'

/** Détail d'une réunion — la charge utile de GET /api/v1/meetings/{id}. */
export function meetingDetail(overrides: Record<string, unknown> = {}) {
  return {
    id: MEETING_ID,
    title: 'Réunion du 11/08/2026',
    mode: 'dictaphone',
    status: 'completed',
    meeting_link: null,
    started_at: null,
    ended_at: null,
    duration_sec: 185,
    created_at: '2026-08-11T09:00:00',
    transcription: {
      id: TRANSCRIPTION_ID,
      status: 'completed',
      raw_text: TRANSCRIPTION_TEXT,
      diarization: [
        { speaker: 'Locuteur 1', start: 0, end: 12, text: 'Bonjour à tous.' },
        { speaker: 'Locuteur 2', start: 12, end: 30, text: 'Le trimestre est en avance.' },
      ],
      language: 'fr',
      processing_ms: 4200,
    },
    summary: null,
    ...overrides,
  }
}

export const VIDEO_TRANSCRIPTION_TEXT =
  'Bonjour à tous, merci d\'être présents. Nous ouvrons le comité de pilotage.'

/**
 * Détail d'une réunion vidéo.
 *
 * La diarisation porte ici des noms de participants, là où le dictaphone ne
 * distingue que « Locuteur 1 » et « Locuteur 2 » : le bot est identifié dans
 * la conférence et reçoit les noms déclarés par les participants. C'est la
 * différence visible la plus nette entre les deux modes.
 */
export function videoMeetingDetail(overrides: Record<string, unknown> = {}) {
  return meetingDetail({
    id:           VIDEO_MEETING_ID,
    title:        'Comité de pilotage',
    mode:         'video',
    meeting_link: MEETING_LINK,
    duration_sec: 2730,
    transcription: {
      id:            TRANSCRIPTION_ID,
      status:        'completed',
      raw_text:      VIDEO_TRANSCRIPTION_TEXT,
      diarization: [
        { speaker: 'Sophie Marchand', start: 0,   end: 45,  text: 'Bonjour à tous, merci d\'être présents.' },
        { speaker: 'Marc Lefèvre',    start: 45,  end: 92,  text: 'Le chantier de migration est terminé.' },
        { speaker: 'Sophie Marchand', start: 92,  end: 130, text: 'Très bien, passons au budget.' },
      ],
      language:      'fr',
      processing_ms: 8400,
    },
    ...overrides,
  })
}

/**
 * Détail d'une réunion.
 *
 * Le motif s'arrête à un seul segment : dans la glob Playwright, `*` ne
 * traverse pas les `/`, donc les sous-routes comme .../audio ne sont pas
 * attrapées ici.
 */
export async function mockMeetingDetail(page: Page, detail = meetingDetail()) {
  await page.route('**/api/v1/meetings/*', (route) => {
    if (route.request().method() !== 'GET') return route.fallback()

    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(detail),
    })
  })
}

/** Enregistrement du consentement RGPD. */
export async function mockConsent(page: Page) {
  await page.route('**/api/v1/consents', (route) =>
    route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({
        id: '11111111-1111-1111-1111-111111111111',
        given_at: '2026-08-11T09:00:00',
      }),
    })
  )
}
