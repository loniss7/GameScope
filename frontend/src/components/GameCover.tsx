import { Box, Image } from '@mantine/core';
import { IconDeviceGamepad2 } from '@tabler/icons-react';
import { useState } from 'react';

type GameCoverProps = {
  src: string | null;
  alt: string;
  className?: string;
};

export default function GameCover({ src, alt, className }: GameCoverProps) {
  const [failed, setFailed] = useState(false);

  if (!src || failed) {
    return (
      <Box className={`cover-placeholder ${className ?? ''}`} aria-hidden="true">
        <IconDeviceGamepad2 size={36} stroke={1.2} />
        <span>GAMESCOPE</span>
      </Box>
    );
  }

  return (
    <Image
      src={src}
      alt={alt}
      className={className}
      fit="cover"
      onError={() => setFailed(true)}
    />
  );
}
