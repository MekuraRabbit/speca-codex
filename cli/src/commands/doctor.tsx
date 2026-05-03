import { Box, Text, useApp } from "ink";
import { useEffect, useState } from "react";
import { Layout } from "../components/Layout.js";
import { runAllChecks, type CheckResult } from "../lib/checks.js";

const ICON: Record<CheckResult["status"], string> = {
  ok: "[OK]",
  warn: "[WARN]",
  fail: "[FAIL]",
  skip: "[SKIP]",
};

export function DoctorCommand() {
  const { exit } = useApp();
  const [results, setResults] = useState<CheckResult[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    runAllChecks().then((rs) => {
      if (cancelled) return;
      setResults(rs);
      const failed = rs.some((r) => r.status === "fail");
      // Allow Ink one tick to render the final state before tearing down.
      setTimeout(() => exit(failed ? new Error("doctor: required checks failed") : undefined), 30);
    });
    return () => {
      cancelled = true;
    };
  }, [exit]);

  if (!results) {
    return (
      <Layout title="speca doctor">
        <Text>Running diagnostics…</Text>
      </Layout>
    );
  }

  const failed = results.some((r) => r.status === "fail");
  const status = failed
    ? "Some required checks failed. See above for fix hints."
    : "All required checks passed.";

  return (
    <Layout title="speca doctor" status={status}>
      {results.map((r) => (
        <Box key={r.name} flexDirection="column">
          <Text>
            <Text bold>{ICON[r.status]} </Text>
            {r.name.padEnd(8)} {r.detail}
          </Text>
          {r.hint ? <Text dimColor>          → {r.hint}</Text> : null}
        </Box>
      ))}
    </Layout>
  );
}
