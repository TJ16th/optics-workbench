import { expect, test } from '@playwright/test'

async function expectKeyboardToggletip(page: import('@playwright/test').Page, termId: string) {
  const root = page.getByTestId(`term-help-${termId}`).first()
  const button = root.getByRole('button').first()
  const content = page.getByTestId(`term-help-content-${termId}`)

  await root.scrollIntoViewIfNeeded()
  await button.focus()
  await expect(button).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(content).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(content).toBeHidden()
}

test('surface header and metric term help support keyboard open and close', async ({ page }) => {
  await page.goto('/?lng=en')
  await expect(page.getByText('Optics Workbench')).toBeVisible()

  await page.getByRole('button', { name: 'System', exact: true }).click()
  await expectKeyboardToggletip(page, 'radius_mm')

  await page.getByRole('button', { name: 'Preview', exact: true }).click()
  await expectKeyboardToggletip(page, 'ray_fan')
})
