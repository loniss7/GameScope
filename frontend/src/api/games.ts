import { ApiError, apiGet, apiPost } from './client';
import type {
  Game,
  GameAchievementsResponse,
  GameReviewsResponse,
  GameSummary,
} from './types';

export async function searchGames(query: string, signal?: AbortSignal) {
  const params = new URLSearchParams({ q: query.trim(), limit: '20' });
  return apiGet<{ items: Game[] }>(`/api/games/search?${params.toString()}`, signal);
}

export async function getGame(id: string, signal?: AbortSignal) {
  return apiGet<Game>(`/api/games/${encodeURIComponent(id)}`, signal);
}

export async function getGameReviews(id: string, limit: number, signal?: AbortSignal) {
  const params = new URLSearchParams({ limit: String(limit) });
  return apiGet<GameReviewsResponse>(
    `/api/games/${encodeURIComponent(id)}/reviews?${params.toString()}`,
    signal,
  );
}

export async function getGameAchievements(id: string, signal?: AbortSignal) {
  return apiGet<GameAchievementsResponse>(
    `/api/games/${encodeURIComponent(id)}/achievements`,
    signal,
  );
}

export async function getGameSummary(id: string, signal?: AbortSignal): Promise<GameSummary | null> {
  try {
    return await apiGet<GameSummary>(`/api/games/${encodeURIComponent(id)}/summary`, signal);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

export async function createGameSummary(
  id: string,
  options: { language?: string; forceRefresh?: boolean } = {},
  signal?: AbortSignal,
) {
  const params = new URLSearchParams({ language: options.language ?? 'ru' });
  if (options.forceRefresh) params.set('force_refresh', 'true');
  return apiPost<GameSummary>(
    `/api/games/${encodeURIComponent(id)}/summary?${params.toString()}`,
    signal,
  );
}
