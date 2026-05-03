import { Text } from "ink";
import { Layout } from "../components/Layout.js";

interface VersionCommandProps {
  version: string;
}

export function VersionCommand({ version }: VersionCommandProps) {
  return (
    <Layout title="speca-cli">
      <Text>v{version}</Text>
    </Layout>
  );
}
