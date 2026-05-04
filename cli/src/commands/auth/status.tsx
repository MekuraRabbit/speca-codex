/**
 * `speca auth status` — list every account in the local store with its type,
 * scope summary, and time-to-expiry.
 *
 * Renders via Ink so the layout matches `speca doctor`.
 */

import { Box, Text, useApp } from "ink";
import { useEffect, useState } from "react";
import { Layout } from "../../components/Layout.js";
import { REQUIRED_OAUTH_SCOPE } from "../../auth/check.js";
import { listAccounts, type Account } from "../../auth/store.js";

interface Row {
  id: string;
  account: Account;
}

function formatRemaining(ms: number): string {
  if (ms <= 0) return "Expired";
  const mins = Math.floor(ms / 60_000);
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  const rem = mins % 60;
  if (hrs < 24) return `${hrs}h ${rem}m`;
  const days = Math.floor(hrs / 24);
  const remH = hrs % 24;
  return `${days}d ${remH}h`;
}

function describe(row: Row, now: number): { kind: string; expiry: string; scopes: string } {
  if (row.account.type === "apikey") {
    return {
      kind: "api-key",
      expiry: "n/a",
      scopes: "n/a",
    };
  }
  const remaining = row.account.expires_at - now;
  const hasRequired = row.account.scopes.includes(REQUIRED_OAUTH_SCOPE);
  return {
    kind: "oauth",
    expiry: formatRemaining(remaining),
    scopes: hasRequired
      ? `${row.account.scopes.length} (incl. ${REQUIRED_OAUTH_SCOPE})`
      : `${row.account.scopes.length} (MISSING ${REQUIRED_OAUTH_SCOPE})`,
  };
}

interface StatusCommandProps {
  /** Override the auth.json path (used by tests). */
  authFile?: string;
  /** Inject "now" for deterministic snapshots. */
  now?: number;
}

export function StatusCommand({ authFile, now: nowProp }: StatusCommandProps = {}) {
  const { exit } = useApp();
  const [rows, setRows] = useState<Row[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listAccounts(authFile)
      .then((rs) => {
        if (cancelled) return;
        setRows(rs);
        setTimeout(() => exit(undefined), 30);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError((err as Error).message);
        setTimeout(() => exit(new Error("status: failed to read auth store")), 30);
      });
    return () => {
      cancelled = true;
    };
  }, [authFile, exit]);

  if (error) {
    return (
      <Layout title="speca auth status" status="failed to read auth store">
        <Text color="red">Error: {error}</Text>
      </Layout>
    );
  }

  if (!rows) {
    return (
      <Layout title="speca auth status">
        <Text>Loading…</Text>
      </Layout>
    );
  }

  if (rows.length === 0) {
    return (
      <Layout title="speca auth status" status="No accounts found">
        <Text>Not logged in. Run `speca auth login`.</Text>
      </Layout>
    );
  }

  const now = nowProp ?? Date.now();

  return (
    <Layout title="speca auth status" status={`${rows.length} account(s) on file`}>
      {rows.map((r) => {
        const d = describe(r, now);
        return (
          <Box key={r.id} flexDirection="column" marginBottom={1}>
            <Text>
              <Text bold>{r.id}</Text> <Text dimColor>({d.kind})</Text>
            </Text>
            <Text dimColor>          scopes : {d.scopes}</Text>
            <Text dimColor>          expires: {d.expiry}</Text>
          </Box>
        );
      })}
    </Layout>
  );
}
