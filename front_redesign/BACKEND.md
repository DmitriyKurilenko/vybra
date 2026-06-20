# Контракт бэкенда

Клиент (`src/api/client.js`) ожидает эти эндпоинты, когда задан `VITE_API_URL`.
Все тела — JSON. Куки/сессия — `credentials: 'include'`.

## Модель товара

```jsonc
{
  "id": "nb",                 // string, уникальный
  "n": "Кроссовки NB 530",    // название
  "p": "8 990 ₽",             // цена строкой (клиент парсит число для бюджета)
  "s": "WB",                  // источник: WB | OZON | URL
  "cat": "shoes",             // категория (см. CAT в theme/tokens.js)
  "elo": 1280,                // текущий рейтинг
  "r": 4.8                    // рейтинг отзывов 0..5
}
```

## Эндпоинты

| Метод | Путь              | Тело запроса                  | Ответ |
|-------|-------------------|-------------------------------|-------|
| GET   | `/api/state`      | —                             | `{ items: Item[], matches: number, budget: number }` |
| POST  | `/api/matches`    | `{ winnerId, loserId }`       | `{ items: Item[], matches: number }` |
| POST  | `/api/items`      | `{ n, p, s, cat, r? }`        | `Item` (с присвоенным `id`, `elo=1200`) |
| DELETE| `/api/items/:id`  | —                             | `204` |
| PUT   | `/api/budget`     | `{ budget: number }`          | `{ budget: number }` |
| POST  | `/api/preview`    | `{ url }`                     | `{ n, p, s, cat }` — распарсенная карточка по ссылке |
| POST  | `/api/reset`      | —                             | `{ items, matches, budget }` |

## Важно про ELO

`POST /api/matches` должен **сам пересчитывать рейтинг на сервере** и возвращать
обновлённый список. Клиент НЕ присылает новые значения elo — только кто победил.
Формула (как в `src/lib/elo.js`, k=24):

```
expW = 1 / (1 + 10^((loserElo - winnerElo) / 400))
winnerElo += round(24 * (1 - expW))
loserElo  += round(24 * (0 - (1 - expW)))
```

Так рейтинг нельзя накрутить с клиента.

## Подбор пары

Сейчас пару близких по рейтингу товаров клиент выбирает сам (`pickPair`).
Если хочешь серверный подбор — добавь `GET /api/pair → { a: Item, b: Item }`
и вызови его в `state/useApp.js` вместо `api.nextPair`.
