const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
).replace(/\/$/, '');

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

function getDetail(payload: unknown): { message?: string; code?: string } {
  if (!payload || typeof payload !== 'object' || !('detail' in payload)) {
    return {};
  }

  const detail = payload.detail;
  if (typeof detail === 'string') return { message: detail };
  if (detail && typeof detail === 'object') {
    const message = 'message' in detail && typeof detail.message === 'string' ? detail.message : undefined;
    const code = 'code' in detail && typeof detail.code === 'string' ? detail.code : undefined;
    return { message, code };
  }

  return {};
}

export async function apiGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ApiError('Не удалось связаться с GameScope API.', 0);
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    payload = undefined;
  }

  if (!response.ok) {
    const detail = getDetail(payload);
    throw new ApiError(detail.message ?? `HTTP ${response.status}`, response.status, detail.code);
  }

  return payload as T;
}

export async function apiPost<T>(path: string, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: 'POST',
      headers: { Accept: 'application/json' },
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ApiError('Не удалось связаться с GameScope API.', 0);
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    payload = undefined;
  }

  if (!response.ok) {
    const detail = getDetail(payload);
    throw new ApiError(detail.message ?? `HTTP ${response.status}`, response.status, detail.code);
  }

  return payload as T;
}

export function getApiErrorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return 'Произошла непредвиденная ошибка. Попробуйте ещё раз.';

  switch (error.code) {
    case 'steam_api_key_missing':
      return 'Steam-данные временно недоступны: на backend не настроен ключ Steam API.';
    case 'summary_unavailable':
      return 'AI-анализ недоступен: для этой игры нет Steam ID или отзывов.';
    case 'ai_provider_error':
      return 'AI-провайдер вернул ошибку. Попробуйте повторить запрос позже.';
    case 'ai_provider_unavailable':
      return 'AI-провайдер временно недоступен. Попробуйте повторить запрос позже.';
  }

  switch (error.status) {
    case 0:
      return 'Не удалось подключиться к API. Проверьте, запущен ли backend.';
    case 404:
      return 'Игра не найдена. Вернитесь к поиску и выберите другой результат.';
    case 422:
      return 'Запрос не прошёл проверку. Измените его и попробуйте снова.';
    case 502:
    case 503:
      return 'Источник данных временно недоступен. Попробуйте повторить запрос чуть позже.';
    default:
      return 'Не удалось загрузить данные. Попробуйте ещё раз.';
  }
}
