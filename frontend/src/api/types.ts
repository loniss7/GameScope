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
