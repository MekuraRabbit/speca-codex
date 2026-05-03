import { Box, Text } from "ink";
import type { ReactNode } from "react";

interface LayoutProps {
  title: string;
  status?: string;
  children: ReactNode;
}

export function Layout({ title, status, children }: LayoutProps) {
  return (
    <Box flexDirection="column">
      <Box borderStyle="round" paddingX={1} marginBottom={1}>
        <Text bold>{title}</Text>
      </Box>
      <Box flexDirection="column" paddingX={1}>
        {children}
      </Box>
      {status ? (
        <Box paddingX={1} marginTop={1}>
          <Text dimColor>{status}</Text>
        </Box>
      ) : null}
    </Box>
  );
}
