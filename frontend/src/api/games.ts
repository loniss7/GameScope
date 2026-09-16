import { apiGet } from './client';
import type { Game, GameReviewsResponse } from './types';

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
