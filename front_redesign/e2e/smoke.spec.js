import { test, expect } from '@playwright/test';

const password = 'E2ePass12345';

test('registration and manual wishlist item creation work', async ({ page }) => {
  const email = `e2e-${Date.now()}-${Math.random().toString(16).slice(2)}@vybra.test`;

  await page.addInitScript(() => {
    window.localStorage.setItem('vybra_onb_done', '1');
    window.localStorage.removeItem('vybra_flow_done');
  });

  await page.goto('/app/');

  await expect(page.getByText('С возвращением')).toBeVisible();
  await page.getByRole('button', { name: 'Зарегистрироваться' }).click();
  await expect(page.getByText('Создать аккаунт')).toBeVisible();
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Пароль').fill(password);
  await page.getByRole('button', { name: /Зарегистрироваться/ }).click();

  await expect(page.getByText('Подключи источники')).toBeVisible();
  await page.getByRole('button', { name: /Продолжить/ }).click();

  await page.getByRole('button', { name: /Избранное/ }).click();
  await expect(page.getByText(/0 товаров/)).toBeVisible();

  await page.getByRole('button', { name: /Добавить/ }).click();
  await expect(page.getByText('Добавить товар')).toBeVisible();
  await page.getByRole('button', { name: 'Вручную' }).click();
  await page.getByLabel('Название').fill('E2E товар Playwright');
  await page.getByLabel('Цена, ₽').fill('12990');
  await page.getByRole('button', { name: /Добавить в избранное/ }).click();

  await expect(page.getByText('E2E товар Playwright')).toBeVisible();
  await expect(page.getByText(/1 товаров/)).toBeVisible();
});
