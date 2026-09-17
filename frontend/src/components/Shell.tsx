import { AppShell, Anchor, Badge, Box, Container, Group, Text, UnstyledButton } from '@mantine/core';
import { IconDeviceGamepad2, IconSearch } from '@tabler/icons-react';
import { Link, Outlet, useLocation } from 'react-router-dom';

export default function Shell() {
  const location = useLocation();
  const isHome = location.pathname === '/';

  return (
    <AppShell header={{ height: 72 }} padding={0}>
      <AppShell.Header className="app-header">
        <Container size="xl" h="100%">
          <Group justify="space-between" h="100%" wrap="nowrap">
            <Group gap="xl" className="brand-cluster" wrap="nowrap">
              <UnstyledButton component={Link} to="/" className="brand-link" aria-label="GameScope — главная">
                <Box className="brand-mark"><IconDeviceGamepad2 size={23} stroke={1.8} /></Box>
                <Text className="brand-name">GAME<span>SCOPE</span></Text>
              </UnstyledButton>
              <Anchor component={Link} to="/" className={isHome ? 'nav-link nav-link-active' : 'nav-link'}>
                Каталог
              </Anchor>
            </Group>

            <Badge className="beta-badge" variant="light" color="cyan" radius="xl" leftSection={<IconSearch size={12} />}>
              БЕТА
            </Badge>
          </Group>
        </Container>
      </AppShell.Header>

      <AppShell.Main>
        <Outlet />
        <Box component="footer" className="site-footer">
          <Container size="xl">
            <Group justify="space-between" gap="xs" wrap="wrap">
              <Text className="footer-brand">GAMESCOPE Агрегатор видеоигр</Text>
              <Text className="footer-note">Данные каталога предоставляются открытыми игровыми источниками</Text>
            </Group>
          </Container>
        </Box>
      </AppShell.Main>
    </AppShell>
  );
}
