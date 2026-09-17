import { useQuery } from '@tanstack/react-query';
import {
  Anchor,
  Badge,
  Button,
  Container,
  Divider,
  Grid,
  Group,
  Paper,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { IconArrowLeft, IconArrowUpRight, IconCalendar, IconMessageCircle } from '@tabler/icons-react';
import { Link, useParams } from 'react-router-dom';
import { getGame } from '../api/games';
import { formatDate, formatMoney } from '../format';
import ApiErrorAlert from '../components/ApiErrorAlert';
import AchievementsSection from '../components/AchievementsSection';
import GameCover from '../components/GameCover';
import RatingPanel from '../components/RatingPanel';

function ValueList({ label, values }: { label: string; values: string[] }) {
  if (!values.length) return null;
  return (
    <Group className="detail-value-row" align="flex-start" gap="md" wrap="nowrap">
      <Text className="detail-label">{label}</Text>
      <Text className="detail-value">{values.join(', ')}</Text>
    </Group>
  );
}

export default function GamePage() {
  const { id = '' } = useParams();
  const gameQuery = useQuery({
    queryKey: ['games', id],
    queryFn: ({ signal }) => getGame(id, signal),
    enabled: Boolean(id),
  });

  if (gameQuery.isLoading) {
    return (
      <Container size="xl" className="page-container">
        <Skeleton height={18} width={150} mb="xl" />
        <Grid gutter="xl">
          <Grid.Col span={{ base: 12, md: 4 }}><Skeleton height={480} radius="lg" /></Grid.Col>
          <Grid.Col span={{ base: 12, md: 8 }}>
            <Stack gap="lg"><Skeleton height={18} width={170} /><Skeleton height={48} width="72%" /><Skeleton height={20} width="52%" /><Skeleton height={170} radius="lg" /></Stack>
          </Grid.Col>
        </Grid>
      </Container>
    );
  }

  if (gameQuery.isError || !gameQuery.data) {
    return (
      <Container size="xl" className="page-container error-page">
        <Button component={Link} to="/" variant="subtle" color="gray" leftSection={<IconArrowLeft size={16} />} className="back-link">К поиску</Button>
        <ApiErrorAlert error={gameQuery.error} onRetry={() => void gameQuery.refetch()} />
      </Container>
    );
  }

  const game = gameQuery.data;
  const releaseDate = formatDate(game.release_date);
  const reviewPath = game.id ? `/games/${encodeURIComponent(game.id)}/reviews` : undefined;
  const priceLabel = game.is_free === true
    ? 'Бесплатно'
    : game.price
      ? formatMoney(game.price.amount, game.price.currency)
      : game.is_free === false
        ? 'Цена не указана'
        : 'Нет данных';

  return (
    <Container size="xl" className="page-container game-page">
      <Group justify="space-between" mb="xl" wrap="wrap" gap="sm">
        <Anchor component={Link} to="/" className="back-link"><IconArrowLeft size={16} /> Назад к поиску</Anchor>
        <Text className="page-overline">КАРТОЧКА ИГРЫ <span> / </span> {game.id ? `GS-${game.id}` : 'GAME'}</Text>
      </Group>

      <Grid gutter={{ base: 'lg', md: 36 }} align="start">
        <Grid.Col span={{ base: 12, md: 4 }}>
          <div className="detail-cover-frame">
            <GameCover src={game.image_url} alt={`Обложка игры ${game.title}`} className="detail-cover" />
            <div className="cover-index" aria-hidden="true">GS / 001</div>
          </div>
          <div className="detail-quick-meta">
            <Group justify="space-between" className="quick-meta-row">
              <Text className="detail-label">Релиз</Text>
              <Text className="detail-value">{releaseDate ?? 'Неизвестно'}</Text>
            </Group>
            <Divider className="dark-divider" />
            <Group justify="space-between" className="quick-meta-row">
              <Text className="detail-label">Стоимость</Text>
              <Text className={game.is_free === true ? 'detail-value free-price' : 'detail-value'}>{priceLabel}</Text>
            </Group>
            {game.achievement_count !== null && (
              <>
                <Divider className="dark-divider" />
                <Group justify="space-between" className="quick-meta-row">
                  <Text className="detail-label">Достижения</Text>
                  <Text className="detail-value">{game.achievement_count}</Text>
                </Group>
              </>
            )}
          </div>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 8 }}>
          <Stack gap="xl">
            <div className="detail-heading">
              <Group gap="xs" mb="sm">
                <Badge variant="light" color="cyan" radius="sm">КАТАЛОГ GAMESCOPE</Badge>
                {game.external_ids.steam && <Badge variant="outline" color="gray" radius="sm">STEAM</Badge>}
              </Group>
              <Title order={1} className="detail-title">{game.title}</Title>
              <Group gap="xs" mt="md" className="detail-tags" wrap="wrap">
                {game.genres.map((genre) => <Badge key={genre} variant="light" color="gray" className="detail-tag">{genre}</Badge>)}
                {game.platforms.slice(0, 4).map((platform) => <Badge key={platform} variant="outline" color="gray" className="detail-tag">{platform}</Badge>)}
                {releaseDate && <Badge variant="outline" color="gray" leftSection={<IconCalendar size={12} />} className="detail-tag">{releaseDate}</Badge>}
              </Group>
            </div>

            <div>
              <Group justify="space-between" align="end" mb="sm" gap="xs">
                <div>
                  <Text className="section-kicker">ГОЛОСА ИГРОКОВ</Text>
                  <Title order={3} className="subsection-title">Оценки из разных источников</Title>
                </div>
                <Text className="ratings-caption">Шкалы источников не объединяются</Text>
              </Group>
              {game.ratings.length ? (
                <SimpleGrid cols={{ base: 1, xs: 2, lg: 3 }} spacing="sm">
                  {game.ratings.map((rating, index) => <RatingPanel key={`${rating.source}-${index}`} rating={rating} />)}
                </SimpleGrid>
              ) : (
                <Paper className="quiet-panel" radius="lg" withBorder>
                  <Text className="muted-copy">Оценки пока не доступны.</Text>
                </Paper>
              )}
            </div>

            {game.description && (
              <Paper className="description-panel" radius="lg" withBorder>
                <Group gap="sm" mb="sm"><span className="section-mark" /><Text className="section-kicker">ОБ ИГРЕ</Text></Group>
                <Text className="description-copy">{game.description}</Text>
              </Paper>
            )}

            <div className="detail-data-section">
              <Group gap="sm" mb="md"><span className="section-mark" /><Text className="section-kicker">ДЕТАЛИ</Text></Group>
              <ValueList label="Разработчик" values={game.developers} />
              <ValueList label="Издатель" values={game.publishers} />
              <ValueList label="Категории" values={game.categories} />
              {game.system_requirements && (game.system_requirements.minimum || game.system_requirements.recommended) && (
                <Stack gap="sm" className="requirements-block">
                  {game.system_requirements.minimum && <Group className="detail-value-row" align="flex-start" gap="md" wrap="nowrap"><Text className="detail-label">Минимальные требования</Text><Text className="detail-value requirements-copy">{game.system_requirements.minimum}</Text></Group>}
                  {game.system_requirements.recommended && <Group className="detail-value-row" align="flex-start" gap="md" wrap="nowrap"><Text className="detail-label">Рекомендуемые</Text><Text className="detail-value requirements-copy">{game.system_requirements.recommended}</Text></Group>}
                </Stack>
              )}
            </div>

            {game.id && <AchievementsSection id={game.id} fallbackTotal={game.achievement_count} />}

            {reviewPath ? (
              <Paper className="reviews-cta" radius="lg" withBorder>
                <Group justify="space-between" align="center" gap="md" wrap="wrap">
                  <Group gap="md" wrap="nowrap">
                    <div className="cta-icon"><IconMessageCircle size={22} /></div>
                    <div>
                      <Text className="cta-title">Что говорят игроки?</Text>
                      <Text className="cta-copy">Читай отзывы сообщества Steam</Text>
                    </div>
                  </Group>
                  <Button component={Link} to={reviewPath} rightSection={<IconArrowUpRight size={16} />} className="reviews-button">Читать отзывы</Button>
                </Group>
              </Paper>
            ) : (
              <Text className="muted-copy">Отзывы недоступны: у игры нет внутреннего ID GameScope.</Text>
            )}
          </Stack>
        </Grid.Col>
      </Grid>
    </Container>
  );
}
