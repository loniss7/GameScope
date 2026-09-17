import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Anchor,
  Badge,
  Button,
  Container,
  Group,
  Paper,
  Skeleton,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { IconArrowLeft, IconClock, IconThumbDown, IconThumbUp } from '@tabler/icons-react';
import { Link, useParams } from 'react-router-dom';
import { getGameReviews } from '../api/games';
import { formatCount, formatDate, formatPlaytime, formatSource } from '../format';
import ApiErrorAlert from '../components/ApiErrorAlert';
import AiAnalysisSlot from '../components/AiAnalysisSlot';

export default function ReviewsPage() {
  const { id = '' } = useParams();
  const [limit, setLimit] = useState(20);
  const reviewsQuery = useQuery({
    queryKey: ['games', id, 'reviews', limit],
    queryFn: ({ signal }) => getGameReviews(id, limit, signal),
    enabled: Boolean(id),
    placeholderData: (previousData) => previousData,
  });
  const data = reviewsQuery.data;
  const canLoadMore = Boolean(
    data && limit < 100 && data.items.length >= limit && data.total > data.items.length,
  );

  return (
    <Container size="xl" className="page-container reviews-page">
      <Anchor component={Link} to={`/games/${encodeURIComponent(id)}`} className="back-link"><IconArrowLeft size={16} /> К карточке игры</Anchor>
      <Group justify="space-between" align="end" mt="xl" mb="lg" gap="md" wrap="wrap">
        <div>
          <Text className="section-kicker">ОТЗЫВЫ СООБЩЕСТВА</Text>
          <Title order={1} className="reviews-title">Игроки говорят</Title>
        </div>
        {data && <Badge variant="light" color="gray" radius="xl">{formatCount(data.total)} всего в {formatSource(data.source)}</Badge>}
      </Group>

      {reviewsQuery.isLoading && (
        <Stack gap="md" mt="xl">
          {Array.from({ length: 4 }, (_, index) => <Skeleton key={index} height={144} radius="lg" />)}
        </Stack>
      )}

      {reviewsQuery.isError && <ApiErrorAlert error={reviewsQuery.error} onRetry={() => void reviewsQuery.refetch()} />}

      {reviewsQuery.isSuccess && data && (
        <>
          {data.items.length === 0 ? (
            <Paper className="reviews-empty" radius="lg" withBorder>
              <div className="empty-review-mark">“</div>
              <Text className="reviews-empty-title">Пока нет доступных отзывов</Text>
              <Text className="muted-copy">Для этой игры Steam не вернул отзывы. Возможно, она ещё не связана с каталогом Steam.</Text>
            </Paper>
          ) : (
            <Stack gap="md" className="review-list">
              {data.items.map((review, index) => {
                const playtime = formatPlaytime(review.playtime_minutes);
                const date = formatDate(review.created_at);
                return (
                  <Paper key={`${review.author ?? 'review'}-${review.created_at ?? index}-${index}`} className="review-card" radius="lg" withBorder>
                    <Group justify="space-between" align="flex-start" gap="md" mb="md" wrap="wrap">
                      <Group gap="sm" wrap="nowrap">
                        <div className={review.voted_up ? 'review-vote review-vote-up' : 'review-vote review-vote-down'}>
                          {review.voted_up ? <IconThumbUp size={17} /> : <IconThumbDown size={17} />}
                        </div>
                        <div>
                          <Text className="review-recommendation">{review.voted_up ? 'Рекомендует' : 'Не рекомендует'}</Text>
                          <Text className="review-author">{review.author ? `Игрок Steam · ${review.author}` : 'Игрок Steam'}</Text>
                        </div>
                      </Group>
                      <Group gap="xs" className="review-meta" wrap="wrap">
                        {date && <Badge variant="outline" color="gray" radius="sm">{date}</Badge>}
                        {review.language && <Badge variant="outline" color="gray" radius="sm">{review.language}</Badge>}
                        {playtime && <Badge variant="outline" color="gray" radius="sm" leftSection={<IconClock size={12} />}>{playtime} в игре</Badge>}
                      </Group>
                    </Group>
                    <Text className="review-text">{review.text}</Text>
                  </Paper>
                );
              })}
            </Stack>
          )}

          {canLoadMore && (
            <Group justify="center" mt="xl">
              <Button variant="light" color="cyan" loading={reviewsQuery.isFetching} onClick={() => setLimit((current) => Math.min(100, current + 20))}>
                Показать ещё отзывы
              </Button>
            </Group>
          )}
          <Text className="review-limit-note">Загружено {data.items.length} из {formatCount(data.total)} отзывов</Text>
        </>
      )}

      {id && <AiAnalysisSlot key={id} gameId={id} />}
    </Container>
  );
}
