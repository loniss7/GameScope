export function formatDate(value: string | null): string | null {
  if (!value) return null;
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(date);
}

export function formatCount(value: number): string {
  return new Intl.NumberFormat('ru-RU', { notation: 'compact', maximumFractionDigits: 1 }).format(value);
}

export function formatPlaytime(minutes: number | null): string | null {
  if (minutes === null) return null;
  const hours = Math.floor(minutes / 60);
  if (hours === 0) return `${minutes} мин`;
  return `${new Intl.NumberFormat('ru-RU').format(hours)} ч`;
}

export function formatMoney(amount: string, currency: string): string {
  const numericAmount = Number(amount);
  if (!Number.isFinite(numericAmount)) return `${amount} ${currency}`;

  try {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency,
      maximumFractionDigits: 2,
    }).format(numericAmount);
  } catch {
    return `${amount} ${currency}`;
  }
}

export function formatSource(source: string): string {
  const known: Record<string, string> = {
    rawg: 'RAWG',
    steam: 'Steam',
    metacritic: 'Metacritic',
  };
  return known[source.toLowerCase()] ?? source;
}
