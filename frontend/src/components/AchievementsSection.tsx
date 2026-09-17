import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Accordion,
  Alert,
  Badge,
  Box,
  Button,
  Group,
  Image,
  Loader,
  Paper,
  SimpleGrid,
  Text,
  ThemeIcon,
} from '@mantine/core';
import { IconLock, IconTrophy } from '@tabler/icons-react';
import { getGameAchievements } from '../api/games';
import { getApiErrorMessage } from '../api/client';
import type { GameAchievement } from '../api/types';

function AchievementIcon({ achievement }: { achievement: GameAchievement }) {
  const [failed, setFailed] = useState(false);
  const source = achievement.hidden ? achievement.icon_gray_url ?? achievement.icon_url : achievement.icon_url;

  if (!source || failed) {
    return (
      <ThemeIcon size={48} radius="md" variant="light" color={achievement.hidden ? 'gray' : 'cyan'}>
        {achievement.hidden ? <IconLock size={21} /> : <IconTrophy size={21} />}
      </ThemeIcon>
    );
  }

  return (
    <Image
      src={source}
      alt=""
      w={48}
      h={48}
      radius="md"
      fit="cover"
      className="achievement-icon"
      onError={() => setFailed(true)}
    />
  );
}

export default function AchievementsSection({
  id,
  fallbackTotal,
}: {
  id: string;
  fallbackTotal: number | null;
}) {
  const [opened, setOpened] = useState(false);
  const query = useQuery({
    queryKey: ['games', id, 'achievements'],
    queryFn: ({ signal }) => getGameAchievements(id, signal),
    enabled: opened,
    staleTime: 5 * 60 * 1000,
  });
  const total = query.data?.total ?? fallbackTotal;

  return (
    <Accordion
      className="achievements-section"
      variant="separated"
      value={opened ? 'achievements' : null}
      onChange={(value) => setOpened(Boolean(value))}
    >
      <Accordion.Item value="achievements">
        <Accordion.Control icon={<ThemeIcon size={30} radius="md" variant="light" color="cyan"><IconTrophy size={16} /></ThemeIcon>}>
          <Group gap="sm">
            <Text className="subsection-title">Достижения</Text>
            {total !== null && <Badge variant="light" color="gray" radius="xl">{total}</Badge>}
          </Group>
        </Accordion.Control>
        <Accordion.Panel>
          {query.isLoading && (
            <Group justify="center" py="lg"><Loader size="sm" color="cyan" /></Group>
          )}

          {query.isError && (
            <Alert color="orange" variant="light" title="Не удалось загрузить достижения">
              {getApiErrorMessage(query.error)}
              <Button variant="subtle" color="orange" size="xs" mt="sm" onClick={() => void query.refetch()}>
                Повторить
              </Button>
            </Alert>
          )}

          {query.isSuccess && query.data.items.length === 0 && (
            <Paper className="quiet-panel" radius="md" withBorder>
              <Text className="muted-copy">Для этой игры пока нет доступных достижений.</Text>
            </Paper>
          )}

          {query.isSuccess && query.data.items.length > 0 && (
            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm" className="achievement-list">
              {query.data.items.map((achievement) => (
                <Paper key={achievement.name} className="achievement-row" radius="md" withBorder>
                  <AchievementIcon achievement={achievement} />
                  <Box className="achievement-copy">
                    <Group gap="xs" wrap="nowrap">
                      <Text className="achievement-name">{achievement.display_name || achievement.name}</Text>
                      {achievement.hidden && <Badge size="xs" variant="light" color="gray">Скрытое</Badge>}
                    </Group>
                    {achievement.description && <Text className="achievement-description">{achievement.description}</Text>}
                  </Box>
                </Paper>
              ))}
            </SimpleGrid>
          )}
        </Accordion.Panel>
      </Accordion.Item>
    </Accordion>
  );
}
