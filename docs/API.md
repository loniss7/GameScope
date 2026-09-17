# GameScope Backend API

Описание текущего HTTP API для разработки фронтенда. Контракт сверяется с кодом backend; пока отдельной версии API (`/v1`) нет.

Краткая версия контракта для frontend-агента находится в [FRONTEND_API.md](./FRONTEND_API.md).

## Подключение

- Локальный адрес: `http://127.0.0.1:8000`
- Интерактивная документация FastAPI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
- Авторизация не требуется.
- API принимает и возвращает JSON в UTF-8. Endpoint суммаризации использует `POST` без тела запроса и query-параметры.
- Локальные frontend origins `http://localhost:5173` и `http://127.0.0.1:5173` разрешены настройкой CORS по умолчанию.
- Ключи RAWG, Steam, IGDB/Twitch и других поставщиков остаются только на backend и не должны передаваться из браузера.

Запустить backend из каталога `backend`:

```powershell
python -m uvicorn app.main:app --reload
```

## Сценарий фронтенда

1. Выполнить поиск через `GET /api/games/search?q=...`.
2. Для выбранной игры передать поле `id` из элемента `items` в `GET /api/games/{game_id}`. Это внутренний числовой ID GameScope, сериализованный строкой. Это не ID RAWG или Steam.
3. Для экрана отзывов запросить `GET /api/games/{game_id}/reviews`.
4. Для AI-сводки вызвать `POST /api/games/{game_id}/summary`, затем читать результат через `GET /api/games/{game_id}/summary`.

Поиск основан на RAWG и может вернуть неполные сведения. При запросе деталей backend пытается дополнить запись данными IGDB и Steam и сохраняет результат. Если один из дополнительных поставщиков не находит подходящую игру или временно недоступен, карточка всё равно возвращается с доступными данными. Проверяйте `null` и пустые массивы.

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

Фактический ответ содержит все поля `Game`; пример выше намеренно сокращён. Значения рейтингов в нём иллюстративны и могут меняться. При включённом IGDB дополнительно могут появиться рейтинги `igdb` и `igdb_critics`, а в `external_ids` — идентификатор `igdb` и найденные ссылки на магазины.

### Обогащение из IGDB

IGDB включается только на backend через `IGDB_ENABLED=true` и Twitch credentials. Фронтенд не вызывает IGDB напрямую и не передаёт credentials. При запросе деталей GameScope ищет совпадение по названию, дате релиза и платформам, затем объединяет данные, сохраняя значения RAWG приоритетными.

В стандартную модель `Game` попадают название, описание, дата первого релиза, разработчики, издатели, жанры, режимы игры в `categories`, платформы, обложка, пользовательский рейтинг `igdb` и агрегированный рейтинг критиков `igdb_critics`. Внешние идентификаторы доступны через `external_ids`. Данные франшиз, DLC, скриншотов, видео и времени прохождения пока не вынесены в отдельные frontend endpoint.

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

### `GET /api/games/{game_id}/achievements`

Возвращает опубликованную схему достижений Steam для игры. Для этого запроса используется Steam Web API и переменная окружения `STEAM_API_KEY`, которая настраивается только на backend.

Пример:

```http
GET /api/games/1/achievements
```

Ответ `200 OK`:

```json
{
  "items": [
    {
      "name": "ACH_WIN_1",
      "display_name": "First victory",
      "description": "Win your first match",
      "icon_url": "https://cdn.example/achievement.jpg",
      "icon_gray_url": "https://cdn.example/achievement_gray.jpg",
      "hidden": false
    }
  ],
  "total": 1,
  "source": "steam"
}
```

Если у игры нет связанного Steam ID, endpoint возвращает пустой список. Если `STEAM_API_KEY` не настроен, возвращается `503` с кодом `steam_api_key_missing`.

### `GET /api/games/{game_id}/summary`

Возвращает последнюю сохранённую AI-сводку отзывов Steam. Запрос не вызывает модель и может вернуть `404`, если сводка ещё не создавалась.

Пример ответа `200 OK`:

```json
{
  "summary": "Игроки положительно оценивают сюжет, но часто критикуют оптимизацию.",
  "pros": ["сюжет", "атмосфера"],
  "cons": ["производительность"],
  "sentiment": {
    "positive": 0.78,
    "negative": 0.18,
    "neutral": 0.04
  },
  "reviews_analyzed": 10,
  "reviews_total": 980313,
  "model": "qwen3:8b",
  "source": "steam",
  "language": "ru",
  "generated_at": "2026-09-17T12:00:00Z"
}
```

### `POST /api/games/{game_id}/summary`

Формирует AI-сводку по последним отзывам Steam и сохраняет её в базе данных. Тело запроса не требуется.

Query-параметры:

| Параметр | Тип | Обязательный | По умолчанию | Ограничения |
|---|---|---:|---:|---|
| `language` | string | нет | `ru` | от 2 до 16 символов |
| `force_refresh` | boolean | нет | `false` | при `true` игнорирует совпадающую кэшированную сводку |

Пример:

```http
POST /api/games/1/summary?language=ru
```

Backend передаёт модели не более `AI_MAX_REVIEWS` отзывов, ограничивает длину каждого текста и общий размер промпта через `AI_MAX_PROMPT_CHARS`. Безопасные значения по умолчанию для локальной Ollama: 10 отзывов по 1000 символов, общий промпт — до 12000 символов. Ответ проверяется по схеме `GameSummary`, а повторный запрос с теми же отзывами, моделью и языком использует сохранённую сводку.

Если Ollama не запущена, возвращается `502` с кодом `ai_provider_error`. Если AI-провайдер отключён, возвращается `503` с кодом `ai_provider_unavailable`. При отсутствии Steam ID или отзывов возвращается `422` с кодом `summary_unavailable`.

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
| `ratings` | `GameRating[]` | Оценки разных источников (`rawg`, `metacritic`, `steam`, `igdb`, `igdb_critics`). Не сравнивайте значения без учёта `max_score`. |
| `price` | `GamePrice` или `null` | Цена из Steam, если доступна. |
| `is_free` | boolean или `null` | Бесплатная игра по данным Steam. |
| `achievement_count` | integer или `null` | Количество достижений Steam. |
| `system_requirements` | `GameSystemRequirements` или `null` | Системные требования. |
| `image_url` | string или `null` | URL обложки/изображения. |
| `external_ids` | object `{[provider]: string}` | ID внешних поставщиков, например `rawg`, `steam`, `igdb`, `gog`, `epic`, `xbox` или `playstation`. Не подставляйте их вместо `id` в URL GameScope. |

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

### `GameAchievement`

```json
{
  "name": "ACH_WIN_1",
  "display_name": "First victory",
  "description": "Win your first match",
  "icon_url": "https://cdn.example/achievement.jpg",
  "icon_gray_url": "https://cdn.example/achievement_gray.jpg",
  "hidden": false
}
```

`description`, `icon_url` и `icon_gray_url` могут быть `null`. Поле `hidden` показывает, скрыто ли достижение в Steam.

### `SummarySentiment`

```json
{
  "positive": 0.78,
  "negative": 0.18,
  "neutral": 0.04
}
```

Значения находятся в диапазоне от `0` до `1` и нормализуются backend.

### `GameSummary`

Сводка содержит текстовый вывод модели, часто встречающиеся достоинства и недостатки, распределение тональности, число проанализированных отзывов и метаданные генерации.

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
| `422` | Неверный `game_id`, отсутствующий/пустой `q`, параметр за пределами допустимого диапазона или нет отзывов для сводки. | `{"detail":[{"loc":["query","q"],"msg":"..."}]}` или `{"detail":{"code":"summary_unavailable","message":"..."}}` |
| `502` | Поставщик данных или AI-провайдер вернул ошибку. | `{"detail":{"code":"provider_error","message":"..."}}` или `ai_provider_error`. |
| `503` | Не настроены провайдеры, AI-провайдер или подключение к хранилищу. | `{"detail":{"code":"providers_unavailable","message":"..."}}`, `ai_provider_unavailable` или `database_unavailable`. |
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

export type GameAchievement = {
  name: string;
  display_name: string;
  description: string | null;
  icon_url: string | null;
  icon_gray_url: string | null;
  hidden: boolean;
};

export type GameAchievementsResponse = {
  items: GameAchievement[];
  total: number;
  source: string;
};

export type SummarySentiment = {
  positive: number;
  negative: number;
  neutral: number;
};

export type GameSummary = {
  summary: string;
  pros: string[];
  cons: string[];
  sentiment: SummarySentiment;
  reviews_analyzed: number;
  reviews_total: number;
  model: string;
  source: string;
  language: string;
  generated_at: string | null;
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

export async function getGameAchievements(id: string) {
  const response = await fetch(
    `${API_BASE_URL}/api/games/${encodeURIComponent(id)}/achievements`,
  );
  if (!response.ok) {
    throw new Error(`Achievements failed: HTTP ${response.status}`);
  }
  return (await response.json()) as GameAchievementsResponse;
}

export async function getGameSummary(id: string) {
  const response = await fetch(
    `${API_BASE_URL}/api/games/${encodeURIComponent(id)}/summary`,
  );
  if (!response.ok) {
    throw new Error(`Summary fetch failed: HTTP ${response.status}`);
  }
  return (await response.json()) as GameSummary;
}

export async function createGameSummary(
  id: string,
  options: { language?: string; forceRefresh?: boolean } = {},
) {
  const params = new URLSearchParams();
  if (options.language) params.set("language", options.language);
  if (options.forceRefresh) params.set("force_refresh", "true");
  const query = params.toString();
  const response = await fetch(
    `${API_BASE_URL}/api/games/${encodeURIComponent(id)}/summary${query ? `?${query}` : ""}`,
    { method: "POST" },
  );
  if (!response.ok) {
    throw new Error(`Summary generation failed: HTTP ${response.status}`);
  }
  return (await response.json()) as GameSummary;
}
```

В примере предполагаются типы TypeScript, соответствующие моделям выше. Для production-клиента стоит централизовать обработку ответов `4xx/5xx` и показывать пользователю понятные сообщения.

## Что пока не реализовано в API

- Персональные рекомендации и чат с моделью отсутствуют.
- Пользовательская авторизация и персональные списки игр отсутствуют.
- В поиске нет offset/cursor-пагинации.
- Отдельные endpoint для IGDB-медиа, франшиз, связанных игр и времени прохождения пока отсутствуют.
