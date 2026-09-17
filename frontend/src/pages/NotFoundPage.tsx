import { Button, Container, Stack, Text, Title } from '@mantine/core';
import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <Container size="xl" className="not-found-page">
      <Stack align="center" gap="md">
        <Text className="not-found-code">404</Text>
        <Title order={1} className="not-found-title">Похоже, эта игра затерялась</Title>
        <Text className="muted-copy">Такой страницы нет в каталоге. Вернёмся к поиску?</Text>
        <Button component={Link} to="/" className="reviews-button" mt="sm">Открыть каталог</Button>
      </Stack>
    </Container>
  );
}
