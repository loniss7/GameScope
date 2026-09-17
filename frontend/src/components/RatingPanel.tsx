import { Badge, Group, Paper, RingProgress, Stack, Text } from '@mantine/core';
import { IconStar } from '@tabler/icons-react';
import type { GameRating } from '../api/types';
import { formatCount, formatSource } from '../format';

const ratingColors: Record<string, string> = {
  steam: 'teal.4',
  rawg: 'cyan.4',
  metacritic: 'lime.4',
  igdb: 'violet.4',
  igdb_critics: 'orange.4',
};

export default function RatingPanel({ rating }: { rating: GameRating }) {
  const percent = Math.max(0, Math.min(100, (rating.score / rating.max_score) * 100));
  const color = ratingColors[rating.source.toLowerCase()] ?? 'cyan.4';

  return (
    <Paper className="rating-panel" radius="lg" withBorder>
      <Group gap="md" wrap="nowrap">
        <RingProgress
          size={86}
          thickness={7}
          roundCaps
          sections={[{ value: percent, color }]}
          rootColor="rgba(255,255,255,0.07)"
          label={
            <Text className="ring-value" ta="center">
              {rating.score.toLocaleString('ru-RU', { maximumFractionDigits: 1 })}
            </Text>
          }
        />
        <Stack gap={5}>
          <Badge variant="light" color={color} radius="sm" className="source-badge">
            {formatSource(rating.source)}
          </Badge>
          <Text className="rating-scale">из {rating.max_score}</Text>
          {rating.rating_count !== null && (
            <Text className="rating-count"><IconStar size={12} /> {formatCount(rating.rating_count)} оценок</Text>
          )}
        </Stack>
      </Group>
    </Paper>
  );
}
