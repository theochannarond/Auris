import { test as setup } from '@playwright/test'

const authFile = 'e2e/fixtures/.auth.json'

setup('inject fake auth token', async ({ page }) => {
  await page.route('**/api/v1/auth/register', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ id: '33333333-3333-3333-3333-333333333333' }),
    })
  )

  await page.goto('/')

  await page.evaluate(() => {
    const fakeToken = [
      'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9',
      'eyJzdWIiOiIzMzMzMzMzMy0zMzMzLTMzMzMtMzMzMy0zMzMzMzMzMzMzMzMiLCJlbWFpbCI6InRlc3RAYXVyaXMuZnIifQ',
      'fake-signature'
    ].join('.');
    localStorage.setItem('access_token', fakeToken);
  });

  await page.context().storageState({ path: authFile });
});