import { apiGet } from './client';

export type HealthResponse = {
  status: string;
};

export function getHealth(signal?: AbortSignal) {
  return apiGet<HealthResponse>('/health', signal);
}
