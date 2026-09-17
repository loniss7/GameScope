# GameScope API: контракт для frontend

Этот файл предназначен для frontend-агента. Полная backend-документация находится в [API.md](./API.md), а интерактивная схема доступна по адресу `http://127.0.0.1:8000/docs`.

## Подключение

```ts
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
```

Авторизация пока не требуется. Backend разрешает локальные origins `http://localhost:5173` и `http://127.0.0.1:5173`. Ключи RAWG, Steam и IGDB/Twitch не должны попадать в браузер.

## Основной сценарий

1. Выполнить поиск игры.
2. Сохранить `items[].id` выбранного результата как внутренний ID GameScope.
3. Загрузить карточку игры по этому ID.
4. При необходимости загрузить Steam-отзывы и достижения.
5. Для AI-сводки сначала вызвать `POST summary`, затем получить результат через `GET summary`.

`id` в URL — внутренний числовой ID GameScope, а значения в `external_ids` — идентификаторы RAWG, Steam, IGDB и магазинов.

## Endpoint

| Метод | URL | Назначение |
|---|---|---|
| `GET` | `/health` | Проверка доступности HTTP-приложения |
| `GET` | `/api/games/search?q={query}&limit={limit}` | Поиск игр по названию |
| `GET` | `/api/games/{id}` | Карточка игры и обогащённые метаданные |
| `GET` | `/api/games/{id}/reviews?limit={limit}` | Отзывы Steam |
| `GET` | `/api/games/{id}/achievements` | Достижения Steam |
| `GET` | `/api/games/{id}/summary` | Последняя сохранённая AI-сводка |
| `POST` | `/api/games/{id}/summary` | Создание или обновление AI-сводки |

### Поиск

```http
GET /api/games/search?q=Cyberpunk%202077&limit=10
```

Ответ:

```json
{
  "items": [
    {
      "id": "1",
      "title": "Cyberpunk 2077",
      "image_url": "https://example.com/cover.jpg",
      "external_ids": {"rawg": "41494"}
    }
  ]
}
```

`q` обязателен и содержит от 1 до 200 символов. `limit` находится в диапазоне от 1 до 100. Поиск выполняется через RAWG.

### Карточка игры

```http
GET /api/games/1
```

Ответ содержит `Game`. При включённом IGDB backend дополнительно пытается найти совпадение и добавить `igdb`/магазинные IDs, платформы, режимы игры, обложку и рейтинги.

### Отзывы и достижения

```http
GET /api/games/1/reviews?limit=20
GET /api/games/1/achievements
```

Если игра не связана со Steam, возвращается пустой список. Ошибку отсутствующего Steam API key frontend должен показать как недоступность соответствующего блока.

### AI-сводка отзывов

Создание:

```http
POST /api/games/1/summary?language=ru&force_refresh=false
```

Тело запроса отсутствует. `language` по умолчанию равен `ru`, `force_refresh=true` принудительно запускает новую генерацию.

Получение кэша:

```http
GET /api/games/1/summary
```

Ответ:

```json
{
  "summary": "Краткая сводка мнений игроков.",
  "pros": ["сюжет", "атмосфера"],
  "cons": ["оптимизация"],
  "sentiment": {"positive": 0.78, "negative": 0.18, "neutral": 0.04},
  "reviews_analyzed": 10,
  "reviews_total": 980313,
  "model": "qwen3:8b",
  "source": "steam",
  "language": "ru",
  "generated_at": "2026-09-17T12:00:00Z"
}
```

`GET` возвращает `404`, если сводка ещё не создана. `POST` может вернуть `422`, если нет Steam ID или отзывов; `502`, если Steam/Ollama недоступны или локальная модель отклонила запрос; `503`, если AI-провайдер отключён. Генерация может занять время при первом запуске модели.

## TypeScript-модели

```ts
export type GameRating = {
  source: string;
  score: number;
  max_score: number;
  rating_count: number | null;
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
  price: { amount: string; currency: string; discount_percent: number } | null;
  is_free: boolean | null;
  achievement_count: number | null;
  system_requirements: {
    minimum: string | null;
    recommended: string | null;
  } | null;
  image_url: string | null;
  external_ids: Record<string, string>;
};

export type GameSummary = {
  summary: string;
  pros: string[];
  cons: string[];
  sentiment: {
    positive: number;
    negative: number;
    neutral: number;
  };
  reviews_analyzed: number;
  reviews_total: number;
  model: string;
  source: string;
  language: string;
  generated_at: string | null;
};
```

## Источники и отображение

- `rawg` — базовые данные поиска и карточки.
- `steam` — цена, отзывы, достижения и Steam-рейтинг.
- `igdb` — дополнительный рейтинг и мультиплатформенные IDs.
- `igdb_critics` — агрегированный рейтинг критиков IGDB.

Рейтинг всегда нужно отображать вместе с `source` и `max_score`. Поставщики могут быть временно недоступны, поэтому frontend должен корректно обрабатывать `null`, пустые массивы и ошибки `4xx/5xx`.

Ключи внешних API никогда не передаются в query-параметрах frontend-запросов.
