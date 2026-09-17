import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Badge,
  Button,
  Divider,
  Group,
  Loader,
  Paper,
  Progress,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { IconBrain, IconRefresh, IconSparkles } from '@tabler/icons-react';
import { createGameSummary, getGameSummary } from '../api/games';
import { getApiErrorMessage } from '../api/client';
import { formatCount, formatDateTime, formatSource } from '../format';
import type { GameSummary } from '../api/types';

function sentimentPercent(value: number) {
  return Math.round(Math.max(0, Math.min(1, value)) * 100);
}

function SummaryContent({ summary }: { summary: GameSummary }) {
  const positive = sentimentPercent(summary.sentiment.positive);
  const neutral = sentimentPercent(summary.sentiment.neutral);
  const negative = sentimentPercent(summary.sentiment.negative);
  const generatedAt = formatDateTime(summary.generated_at);

  return (
    <Stack gap="lg">
      <Text className="ai-summary-copy">{summary.summary}</Text>

      {(summary.pros.length > 0 || summary.cons.length > 0) && (
        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
          {summary.pros.length > 0 && (
            <div className="ai-points ai-points-positive">
              <Text className="ai-points-title">Сильные стороны</Text>
              <Stack gap="xs">
                {summary.pros.map((item, index) => <Text key={`${item}-${index}`} className="ai-point">{item}</Text>)}
              </Stack>
            </div>
          )}
          {summary.cons.length > 0 && (
            <div className="ai-points ai-points-negative">
              <Text className="ai-points-title">Что критикуют</Text>
              <Stack gap="xs">
                {summary.cons.map((item, index) => <Text key={`${item}-${index}`} className="ai-point">{item}</Text>)}
              </Stack>
            </div>
          )}
        </SimpleGrid>
      )}

      <div className="sentiment-block">
        <Group justify="space-between" mb="xs">
          <Text className="ai-points-title">Тональность отзывов</Text>
          <Text className="muted-copy">{formatCount(summary.reviews_analyzed)} из {formatCount(summary.reviews_total)} отзывов</Text>
        </Group>
        <Progress.Root size="md" radius="xl">
          <Progress.Section value={positive} color="teal.5" />
          <Progress.Section value={neutral} color="gray.5" />
          <Progress.Section value={negative} color="red.5" />
        </Progress.Root>
        <Group gap="md" mt="xs" className="sentiment-legend">
          <Text><span className="sentiment-dot sentiment-dot-positive" /> Позитивные {positive}%</Text>
          <Text><span className="sentiment-dot sentiment-dot-neutral" /> Нейтральные {neutral}%</Text>
          <Text><span className="sentiment-dot sentiment-dot-negative" /> Негативные {negative}%</Text>
        </Group>
      </div>

      <Divider />
      <Group gap="xs" className="ai-meta" wrap="wrap">
        <Badge variant="outline" color="gray">Модель: {summary.model}</Badge>
        <Badge variant="outline" color="gray">Источник: {formatSource(summary.source)}</Badge>
        <Badge variant="outline" color="gray">Язык: {summary.language.toUpperCase()}</Badge>
        {generatedAt && <Text className="muted-copy">Обновлено {generatedAt}</Text>}
      </Group>
    </Stack>
  );
}

export default function AiAnalysisPanel({ gameId }: { gameId: string }) {
  const queryClient = useQueryClient();
  const queryKey = ['games', gameId, 'summary', 'ru'];
  const summaryQuery = useQuery({
    queryKey,
    queryFn: ({ signal }) => getGameSummary(gameId, signal),
    enabled: Boolean(gameId),
    retry: false,
  });
  const mutation = useMutation({
    mutationFn: ({ forceRefresh }: { forceRefresh: boolean }) =>
      createGameSummary(gameId, { language: 'ru', forceRefresh }),
    onSuccess: async () => {
      // Keep the API flow explicit: POST creates the summary, GET reads the saved result.
      await queryClient.invalidateQueries({ queryKey });
    },
  });

  const summary = summaryQuery.data;
  const actionError = mutation.error;

  return (
    <Paper className="ai-analysis-panel" radius="lg" withBorder>
      <Group justify="space-between" align="flex-start" gap="md" wrap="wrap" mb="lg">
        <Group gap="sm" wrap="nowrap">
          <div className="ai-analysis-icon"><IconBrain size={22} /></div>
          <div>
            <Text className="section-kicker">AI АНАЛИТИКА ОТЗЫВОВ</Text>
            <Title order={3} className="subsection-title">Что думает сообщество</Title>
          </div>
        </Group>
        {summary && (
          <Button
            variant="subtle"
            color="gray"
            size="xs"
            leftSection={<IconRefresh size={14} />}
            onClick={() => mutation.mutate({ forceRefresh: true })}
            loading={mutation.isPending}
          >
            Обновить анализ
          </Button>
        )}
      </Group>

      {summaryQuery.isLoading && (
        <Stack gap="sm">
          <Skeleton height={18} width="92%" />
          <Skeleton height={18} width="76%" />
          <Skeleton height={72} radius="md" />
        </Stack>
      )}

      {summaryQuery.isError && (
        <Alert color="orange" variant="light" title="Не удалось загрузить AI-анализ">
          {getApiErrorMessage(summaryQuery.error)}
          <Button variant="subtle" color="orange" size="xs" mt="sm" onClick={() => void summaryQuery.refetch()}>
            Повторить
          </Button>
        </Alert>
      )}

      {summaryQuery.isSuccess && !summary && !mutation.isPending && (
        <div className="ai-analysis-empty">
          <IconSparkles size={24} />
          <Text className="ai-empty-title">Анализ отзывов ещё не создан</Text>
          <Text className="muted-copy">Соберём основные темы, сильные стороны и критику на основе отзывов Steam.</Text>
          <Button color="cyan" mt="sm" onClick={() => mutation.mutate({ forceRefresh: false })} loading={mutation.isPending}>
            Сформировать анализ
          </Button>
        </div>
      )}

      {mutation.isPending && (
        <Group gap="sm" className="ai-generation-state"><Loader size="sm" color="cyan" /><Text className="muted-copy">Анализируем отзывы…</Text></Group>
      )}

      {actionError && !mutation.isPending && (
        <Alert color="orange" variant="light" title="Анализ не создан">
          {getApiErrorMessage(actionError)}
          <Button variant="subtle" color="orange" size="xs" mt="sm" onClick={() => mutation.mutate({ forceRefresh: Boolean(summary) })}>
            Повторить
          </Button>
        </Alert>
      )}

      {summary && !mutation.isPending && <SummaryContent summary={summary} />}
    </Paper>
  );
}
