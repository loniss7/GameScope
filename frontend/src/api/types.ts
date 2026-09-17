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
