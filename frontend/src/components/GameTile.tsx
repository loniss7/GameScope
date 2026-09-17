import { Badge, Card, Group, Stack, Text } from '@mantine/core';
import { IconCalendar, IconStar } from '@tabler/icons-react';
import { Link } from 'react-router-dom';
import type { Game } from '../api/types';
import { formatDate, formatSource } from '../format';
import GameCover from './GameCover';

export default function GameTile({ game }: { game: Game }) {
  const rating = game.ratings[0];
  const releaseDate = formatDate(game.release_date);

  return (
    <Card component="article" className="game-tile" padding={0} radius="lg" withBorder>
      <Link to={game.id ? `/games/${encodeURIComponent(game.id)}` : '/'} className="game-tile-link">
        <div className="game-tile-cover-wrap">
          <GameCover src={game.image_url} alt="" className="game-tile-cover" />
          <div className="game-tile-cover-shade" />
          {rating && (
            <Badge className="game-tile-rating" variant="light" color="dark" leftSection={<IconStar size={13} fill="currentColor" />}>
              {rating.score.toFixed(1)} <span className="rating-source">/ {rating.max_score} · {formatSource(rating.source)}</span>
            </Badge>
          )}
        </div>
        <Stack className="game-tile-content" gap="sm">
          <Text component="h3" className="game-tile-title" lineClamp={2}>{game.title}</Text>
          <Group gap={6} className="genre-row" wrap="wrap">
            {game.genres.slice(0, 3).map((genre) => (
              <Badge key={genre} variant="light" color="gray" radius="sm" className="genre-badge">{genre}</Badge>
            ))}
            {!game.genres.length && <Text className="muted-copy">Жанр не указан</Text>}
          </Group>
          <Group justify="space-between" gap="xs" className="game-tile-meta" wrap="nowrap">
            <Text className="tile-platform" lineClamp={1}>{game.platforms.slice(0, 2).join(' · ') || 'Платформы не указаны'}</Text>
            {releaseDate && <Text className="tile-date"><IconCalendar size={13} />{releaseDate.slice(-4)}</Text>}
          </Group>
        </Stack>
      </Link>
    </Card>
  );
}
