import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useDebouncedValue } from '@mantine/hooks';
import {
  Alert,
  Badge,
  Container,
  Group,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { IconInfoCircle, IconSearch } from '@tabler/icons-react';
import { useSearchParams } from 'react-router-dom';
import { searchGames } from '../api/games';
import ApiErrorAlert from '../components/ApiErrorAlert';
import GameTile from '../components/GameTile';

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const urlQuery = searchParams.get('q') ?? '';
  const [inputValue, setInputValue] = useState(urlQuery);
  const [debouncedValue] = useDebouncedValue(inputValue, 350);
  const skipNextDebouncedSync = useRef(false);
  const query = useMemo(() => urlQuery.trim(), [urlQuery]);

  useEffect(() => {
    setInputValue(urlQuery);
    skipNextDebouncedSync.current = true;
  }, [urlQuery]);

  useEffect(() => {
    if (skipNextDebouncedSync.current) {
      skipNextDebouncedSync.current = false;
      return;
    }

    const normalized = debouncedValue.trim();
    if (normalized === urlQuery) return;
    setSearchParams(normalized ? { q: normalized } : {}, { replace: true });
  }, [debouncedValue, urlQuery, setSearchParams]);

  const results = useQuery({
    queryKey: ['games', 'search', query],
    queryFn: ({ signal }) => searchGames(query, signal),
    enabled: query.length > 0,
  });

  const submitSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setInputValue((value) => value.trim());
  };

  return (
    <>
      <section className="search-hero">
        <Container size="xl" className="hero-content search-content-only">
          <form className="search-form search-form-only" onSubmit={submitSearch}>
            <TextInput
              aria-label="Название игры"
              placeholder="Например, Cyberpunk 2077"
              value={inputValue}
              onChange={(event) => setInputValue(event.currentTarget.value.slice(0, 200))}
              maxLength={200}
              className="hero-search-input"
              size="lg"
              radius="md"
            />
          </form>
        </Container>
      </section>

      <Container size="xl" className="catalog-content">
        {!query ? (
          <div className="catalog-prompt">
            <div className="prompt-icon"><IconSearch size={20} /></div>
            <div>
              <Text className="prompt-title">Что сегодня запускаем?</Text>
              <Text className="prompt-copy">Введи название игры, чтобы увидеть карточку, рейтинги и отзывы сообщества.</Text>
            </div>
          </div>
        ) : (
          <Stack gap="xl">
            <Group justify="flex-end" align="end" gap="md" className="results-heading" wrap="wrap">
              {!results.isLoading && results.data && (
                <Badge className="result-count" variant="light" color="gray" radius="xl">
                  {results.data.items.length} {results.data.items.length === 1 ? 'игра' : 'игр'}
                </Badge>
              )}
            </Group>

            {results.isLoading && (
              <SimpleGrid cols={{ base: 1, xs: 2, md: 3, lg: 4 }} spacing="lg">
                {Array.from({ length: 8 }, (_, index) => (
                  <Stack key={index} gap="sm">
                    <Skeleton height={250} radius="lg" />
                    <Skeleton height={18} width="76%" />
                    <Skeleton height={14} width="48%" />
                  </Stack>
                ))}
              </SimpleGrid>
            )}

            {results.isError && <ApiErrorAlert error={results.error} onRetry={() => void results.refetch()} />}

            {results.isSuccess && results.data.items.length === 0 && (
              <Alert className="empty-alert" variant="light" color="gray" icon={<IconInfoCircle size={19} />} title="Ничего не нашлось">
                Попробуй другое название или проверь написание игры.
              </Alert>
            )}

            {results.isSuccess && results.data.items.length > 0 && (
              <SimpleGrid cols={{ base: 1, xs: 2, md: 3, lg: 4 }} spacing="lg" className="game-grid">
                {results.data.items.map((game, index) => <GameTile game={game} key={game.id ?? `${game.title}-${index}`} />)}
              </SimpleGrid>
            )}
          </Stack>
        )}
      </Container>
    </>
  );
}
