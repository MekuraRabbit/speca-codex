import { githubFetch, fetchJsonFile } from './github-client';
import type { GitHubContentItem } from '@/types/github';
import type {
  PhaseId,
  Phase01aData,
  Phase01bData,
  Phase01eData,
  Phase02cData,
  Phase03Data,
  Phase04Data,
  TargetInfo,
  SpecSubGraphs,
  Property,
  PropertyWithCode,
  AuditMapItem,
  ReviewedItem,
} from '@/types/pipeline';

export interface PhaseStatus {
  hasData: boolean;
  itemCount: number;
  fileCount: number;
}

export interface BranchData {
  target: TargetInfo | null;
  phaseStatus: Record<PhaseId, PhaseStatus>;
}

const PHASE_IDS: PhaseId[] = ['01a', '01b', '01e', '02c', '03', '04'];

function emptyPhaseStatus(): Record<PhaseId, PhaseStatus> {
  const status: Partial<Record<PhaseId, PhaseStatus>> = {};
  for (const id of PHASE_IDS) {
    status[id] = { hasData: false, itemCount: 0, fileCount: 0 };
  }
  return status as Record<PhaseId, PhaseStatus>;
}

export async function listOutputFiles(branch: string): Promise<GitHubContentItem[]> {
  try {
    return await githubFetch<GitHubContentItem[]>(
      `/contents/outputs?ref=${encodeURIComponent(branch)}`,
    );
  } catch {
    return [];
  }
}

function filterPartials(files: GitHubContentItem[], phaseId: string): GitHubContentItem[] {
  const prefix = `${phaseId}_PARTIAL_`;
  return files.filter((f) => f.name.startsWith(prefix) && f.name.endsWith('.json'));
}

export async function fetchBranchOverview(branch: string): Promise<BranchData> {
  const files = await listOutputFiles(branch);
  const status = emptyPhaseStatus();

  // Count PARTIAL files per phase
  for (const phaseId of PHASE_IDS) {
    if (phaseId === '01a') {
      const stateFile = files.find((f) => f.name === '01a_STATE.json');
      if (stateFile) {
        status['01a'] = { hasData: true, itemCount: 0, fileCount: 1 };
      }
    } else {
      const partials = filterPartials(files, phaseId);
      if (partials.length > 0) {
        status[phaseId] = { hasData: true, itemCount: 0, fileCount: partials.length };
      }
    }
  }

  // Fetch TARGET_INFO if available
  let target: TargetInfo | null = null;
  const targetFile = files.find((f) => f.name === 'TARGET_INFO.json');
  if (targetFile) {
    try {
      target = await fetchJsonFile<TargetInfo>('outputs/TARGET_INFO.json', branch);
    } catch {
      // ignore
    }
  }

  return { target, phaseStatus: status };
}

// --- Phase-specific data loaders ---

export async function fetchPhase01a(branch: string): Promise<Phase01aData> {
  return fetchJsonFile<Phase01aData>('outputs/01a_STATE.json', branch);
}

async function fetchAndMergePartials<T>(
  branch: string,
  phaseId: string,
  files: GitHubContentItem[],
  resultKey: string,
  dedupeKey: string | null,
): Promise<T[]> {
  const partials = filterPartials(files, phaseId);
  if (partials.length === 0) return [];

  const results = await Promise.all(
    partials.map((f) =>
      fetchJsonFile<Record<string, unknown>>(`outputs/${f.name}`, branch).catch(() => null),
    ),
  );

  const items: T[] = [];
  for (const result of results) {
    if (!result) continue;
    const arr = result[resultKey];
    if (Array.isArray(arr)) {
      items.push(...(arr as T[]));
    }
  }

  if (dedupeKey) {
    const seen = new Map<string, number>();
    for (let i = 0; i < items.length; i++) {
      const key = (items[i] as Record<string, unknown>)[dedupeKey] as string;
      if (key) seen.set(key, i);
    }
    const unique: T[] = [];
    const added = new Set<string>();
    for (let i = 0; i < items.length; i++) {
      const key = (items[i] as Record<string, unknown>)[dedupeKey] as string;
      if (!key || (seen.get(key) === i && !added.has(key))) {
        unique.push(items[i]);
        if (key) added.add(key);
      }
    }
    return unique;
  }

  return items;
}

export async function fetchPhase01b(
  branch: string,
  files?: GitHubContentItem[],
): Promise<Phase01bData> {
  const outputFiles = files ?? (await listOutputFiles(branch));
  const specs = await fetchAndMergePartials<SpecSubGraphs>(
    branch, '01b', outputFiles, 'specs', 'source_url',
  );
  return { specs };
}

export async function fetchPhase01e(
  branch: string,
  files?: GitHubContentItem[],
): Promise<Phase01eData> {
  const outputFiles = files ?? (await listOutputFiles(branch));
  const properties = await fetchAndMergePartials<Property>(
    branch, '01e', outputFiles, 'properties', 'property_id',
  );
  return { properties };
}

export async function fetchPhase02c(
  branch: string,
  files?: GitHubContentItem[],
): Promise<Phase02cData> {
  const outputFiles = files ?? (await listOutputFiles(branch));
  const properties_with_code = await fetchAndMergePartials<PropertyWithCode>(
    branch, '02c', outputFiles, 'properties_with_code', 'property_id',
  );
  return { properties_with_code };
}

export async function fetchPhase03(
  branch: string,
  files?: GitHubContentItem[],
): Promise<Phase03Data> {
  const outputFiles = files ?? (await listOutputFiles(branch));
  const audit_items = await fetchAndMergePartials<AuditMapItem>(
    branch, '03', outputFiles, 'audit_items', 'property_id',
  );
  return { audit_items };
}

export async function fetchPhase04(
  branch: string,
  files?: GitHubContentItem[],
): Promise<Phase04Data> {
  const outputFiles = files ?? (await listOutputFiles(branch));
  const reviewed_items = await fetchAndMergePartials<ReviewedItem>(
    branch, '04', outputFiles, 'reviewed_items', 'property_id',
  );
  return { reviewed_items };
}

type PhaseFetcher = (branch: string, files?: GitHubContentItem[]) => Promise<unknown>;

const PHASE_FETCHERS: Record<PhaseId, PhaseFetcher> = {
  '01a': (branch) => fetchPhase01a(branch),
  '01b': fetchPhase01b,
  '01e': fetchPhase01e,
  '02c': fetchPhase02c,
  '03': fetchPhase03,
  '04': fetchPhase04,
};

export async function fetchPhaseData(
  phaseId: PhaseId,
  branch: string,
  files?: GitHubContentItem[],
): Promise<unknown> {
  const fetcher = PHASE_FETCHERS[phaseId];
  if (!fetcher) throw new Error(`Unknown phase: ${phaseId}`);
  return fetcher(branch, files);
}
