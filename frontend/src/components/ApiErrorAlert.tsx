import { Alert, Button, Group } from '@mantine/core';
import { IconAlertTriangle, IconRefresh } from '@tabler/icons-react';
import { getApiErrorMessage } from '../api/client';

export default function ApiErrorAlert({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <Alert className="api-error" variant="light" color="orange" icon={<IconAlertTriangle size={19} />} title="Не удалось загрузить данные">
      <Group justify="space-between" align="center" gap="md" wrap="wrap">
        <span>{getApiErrorMessage(error)}</span>
        {onRetry && <Button size="xs" variant="light" color="orange" leftSection={<IconRefresh size={15} />} onClick={onRetry}>Повторить</Button>}
      </Group>
    </Alert>
  );
}
