import { defineConfig, devices } from '@playwright/test'

const BASE_URL = 'http://localhost:5173'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,

  // En CI, un .only oublié ferait passer la suite en ne lançant qu'un test
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  reporter: process.env.CI
    ? [['github'], ['html', { open: 'never' }]]
    : [['list']],

  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    // Le dictaphone appelle getUserMedia : sans autorisation accordée d'avance,
    // le navigateur ouvre une invite native que Playwright ne peut pas cliquer
    permissions: ['microphone'],
  },

  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        launchOptions: {
          args: [
            '--use-fake-ui-for-media-stream',     // accepte l'invite micro
            '--use-fake-device-for-media-stream', // flux audio synthétique
          ],
        },
      },
    },
  ],

  // Démarre Vite tout seul : sans ça, la CI n'aurait aucune application à visiter
  webServer: {
    command: 'npm run dev',
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
})
