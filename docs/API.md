# GameScope Backend API

Описание текущего HTTP API для разработки фронтенда. Контракт сверяется с кодом backend; пока отдельной версии API (`/v1`) нет.

## Подключение

- Локальный адрес: `http://127.0.0.1:8000`
- Интерактивная документация FastAPI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
- Авторизация не требуется.
- API принимает и возвращает JSON в UTF-8. Все описанные endpoint используют `GET` без тела запроса.
- Локальные frontend origins `http://localhost:5173` и `http://127.0.0.1:5173` разрешены настройкой CORS по умолчанию.
- Ключи RAWG и других поставщиков остаются только на backend и не должны передаваться из браузера.

Запустить backend из каталога `backend`:

```powershell
python -m uvicorn app.main:app --reload
```

## Сценарий фронтенда

1. Выполнить поиск через `GET /api/games/search?q=...`.
2. Для выбранной игры передать поле `id` из элемента `items` в `GET /api/games/{game_id}`. Это внутренний числовой ID GameScope, сериализованный строкой. Это не ID RAWG или Steam.
3. Для экрана отзывов запросить `GET /api/games/{game_id}/reviews`.

Поиск основан на RAWG и может вернуть неполные сведения. При запросе деталей backend пытается дополнить запись данными Steam и сохраняет результат. Если Steam не находит подходящую игру или временно недоступен, некоторые поля и рейтинг Steam могут отсутствовать. Проверяйте `null` и пустые массивы.

## Endpoints

### `GET /health`

Проверяет, что HTTP-приложение запущено.

Ответ `200 OK`:

```json
{
  "status": "ok"
}
```

Это только проверка доступности приложения: endpoint не проверяет соединение с БД и доступность внешних поставщиков.

### `GET /api/games/search`

Ищет игры по названию.

| Параметр | Тип | Обязательный | Ограничения | По умолчанию |
|---|---|---:|---|---:|
| `q` | string | да | от 1 до 200 символов, не только пробелы | — |
| `limit` | integer | нет | от 1 до 100 | `20` |

Текущий RAWG provider возвращает максимум 20 результатов за запрос, поэтому увеличение `limit` выше 20 не гарантирует больше результатов.

Пример:

```http
GET /api/games/search?q=Cyberpunk%202077&limit=5
```

Ответ `200 OK`:

```json
{
  "items": [
    {
      "id": "1",
      "title": "Cyberpunk 2077",
      "description": null,
      "release_date": "2020-12-10",
      "developers": [],
      "publishers": [],
      "genres": ["Shooter", "Action", "RPG"],
      "categories": [],
      "platforms": ["PC", "PlayStation 5"],
      "ratings": [
        {
          "source": "rawg",
          "score": 4.23,
          "max_score": 5.0,
          "rating_count": 3061
        }
      ],
      "price": null,
      "is_free": null,
      "achievement_count": null,
      "system_requirements": null,
      "image_url": "https://example.com/game.jpg",
      "external_ids": {
        "rawg": "41494"
      }
    }
  ]
}
```

Если совпадений нет, сервер возвращает `200 OK` и `{ "items": [] }`.

### `GET /api/games/{game_id}`

Возвращает сохранённую карточку GameScope. `game_id` — числовой внутренний ID, полученный из `items[].id` поиска.

Пример:

```http
GET /api/games/1
```

Ответ `200 OK` — объект `Game` (его поля описаны ниже). Дополнительный пример полей, которые могут появиться после Steam enrichment:

```json
{
  "id": "1",
  "title": "Cyberpunk 2077",
  "ratings": [
    {"source": "rawg", "score": 4.23, "max_score": 5.0, "rating_count": 3061},
    {"source": "metacritic", "score": 73.0, "max_score": 100.0, "rating_count": null},
    {"source": "steam", "score": 86.89, "max_score": 100.0, "rating_count": 979908}
  ],
  "external_ids": {
    "rawg": "41494",
    "steam": "1091500"
  }
}
```

Фактический ответ содержит все поля `Game`; пример выше намеренно сокращён. Значения рейтингов в нём иллюстративны и могут меняться.

### `GET /api/games/{game_id}/reviews`

Возвращает отзывы Steam для игры. `game_id` — внутренний ID GameScope, а не Steam App ID.

| Параметр | Тип | Обязательный | Ограничения | По умолчанию |
|---|---|---:|---|---:|
| `limit` | integer | нет | от 1 до 100 | `20` |

Пример:

```http
GET /api/games/1/reviews?limit=10
```

Ответ `200 OK`:

```json
{
  "items": [
    {
      "source": "steam",
      "author": "76561198000000000",
      "language": "english",
      "text": "Example review text",
      "voted_up": true,
      "created_at": "2024-01-15",
      "playtime_minutes": 1200
    }
  ],
  "total": 979908,
  "source": "steam"
}
```

`items` содержит не больше `limit` отзывов; `total` — общее число отзывов, сообщённое Steam. Если у игры нет связанного Steam ID, endpoint возвращает `200 OK` с пустым `items` и `total: 0`.

## Модели данных

### `Game`

| Поле | Тип JSON | Примечание |
|---|---|---|
| `id` | string или `null` | Внутренний ID GameScope; в ответах каталога обычно строковое число. |
| `title` | string | Название. |
| `description` | string или `null` | Описание. |
| `release_date` | string (`YYYY-MM-DD`) или `null` | Дата релиза. |
| `developers` | string[] | Разработчики; может быть пустым массивом. |
| `publishers` | string[] | Издатели; может быть пустым массивом. |
| `genres` | string[] | Жанры. |
| `categories` | string[] | Категории. |
| `platforms` | string[] | Платформы. |
| `ratings` | `GameRating[]` | Оценки разных источников. Не сравнивайте значения без учёта `max_score`. |
| `price` | `GamePrice` или `null` | Цена из Steam, если доступна. |
| `is_free` | boolean или `null` | Бесплатная игра по данным Steam. |
| `achievement_count` | integer или `null` | Количество достижений Steam. |
| `system_requirements` | `GameSystemRequirements` или `null` | Системные требования. |
| `image_url` | string или `null` | URL обложки/изображения. |
| `external_ids` | object `{[provider]: string}` | ID внешних поставщиков, например `rawg` и `steam`. Не подставляйте их вместо `id` в URL GameScope. |

### `GameRating`

```json
{
  "source": "rawg",
  "score": 4.23,
  "max_score": 5.0,
  "rating_count": 3061
}
```

`rating_count` может быть `null`. Известные источники: `rawg`, `metacritic`, `steam`; список может расширяться.

### `GamePrice`

```json
{
  "amount": "59.99",
  "currency": "USD",
  "discount_percent": 10
}
```

`amount` сериализуется как десятичная строка; `discount_percent` — целое число от 0 до 100.

### `GameSystemRequirements`

```json
{
  "minimum": "Minimum requirements text",
  "recommended": "Recommended requirements text"
}
```

Оба поля могут быть `null`.

## Ошибки

Ошибки возвращаются в JSON.

| HTTP | Когда возникает | Пример ответа |
|---:|---|---|
| `404` | Игра с таким внутренним ID не найдена. | `{"detail":"Game not found."}` |
| `422` | Неверный `game_id`, отсутствующий/пустой `q` или параметр за пределами допустимого диапазона. | `{"detail":[{"loc":["query","q"],"msg":"..."}]}` |
| `502` | Поставщик вернул ошибку, которую endpoint не смог обработать через сохранённые данные. | `{"detail":{"code":"provider_error","message":"..."}}` |
| `503` | Не настроены провайдеры или подключение к хранилищу. | `{"detail":{"code":"providers_unavailable","message":"..."}}` или `database_unavailable`. |
| `500` | Необработанная внутренняя ошибка сервера. | Детали зависят от режима запуска; frontend должен показать общее сообщение. |

При обновлении уже сохранённой игры backend старается вернуть кэшированную карточку, если внешний поставщик временно недоступен.

## Пример клиента на TypeScript

```ts
export type GameRating = {
  source: string;
  score: number;
  max_score: number;
  rating_count: number | null;
};

export type GamePrice = {
  amount: string;
  currency: string;
  discount_percent: number;
};

export type GameSystemRequirements = {
  minimum: string | null;
  recommended: string | null;
};

export type GameReview = {
  source: string;
  author: string | null;
  language: string | null;
  text: string;
  voted_up: boolean;
  created_at: string | null;
  playtime_minutes: number | null;
};

export type GameReviewsResponse = {
  items: GameReview[];
  total: number;
  source: string;
};

export type Game = {
  id: string | null;
  title: string;
  description: string | null;
  release_date: string | null;
  developers: string[];
  publishers: string[];
  genres: string[];
  categories: string[];
  platforms: string[];
  ratings: GameRating[];
  price: GamePrice | null;
  is_free: boolean | null;
  achievement_count: number | null;
  system_requirements: GameSystemRequirements | null;
  image_url: string | null;
  external_ids: Record<string, string>;
};

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function searchGames(query: string, limit = 20) {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  const response = await fetch(`${API_BASE_URL}/api/games/search?${params}`);
  if (!response.ok) throw new Error(`Game search failed: HTTP ${response.status}`);
  return (await response.json()) as { items: Game[] };
}

export async function getGame(id: string) {
  const response = await fetch(
    `${API_BASE_URL}/api/games/${encodeURIComponent(id)}`,
  );
  if (!response.ok) throw new Error(`Game details failed: HTTP ${response.status}`);
  return (await response.json()) as Game;
}

export async function getGameReviews(id: string, limit = 20) {
  const params = new URLSearchParams({ limit: String(limit) });
  const response = await fetch(
    `${API_BASE_URL}/api/games/${encodeURIComponent(id)}/reviews?${params}`,
  );
  if (!response.ok) throw new Error(`Reviews failed: HTTP ${response.status}`);
  return (await response.json()) as GameReviewsResponse;
}
```

В примере предполагаются типы TypeScript, соответствующие моделям выше. Для production-клиента стоит централизовать обработку ответов `4xx/5xx` и показывать пользователю понятные сообщения.

## Что пока не реализовано в API

- Endpoint для нейросетевых сводок, рекомендаций или чата отсутствует.
- Пользовательская авторизация и персональные списки игр отсутствуют.
- В поиске нет offset/cursor-пагинации.
