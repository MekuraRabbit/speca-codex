import { useParams, Link } from 'react-router-dom';
import { ja } from '@/i18n/ja';
import { Header } from '@/components/layout/Header';
import { SeverityBadge } from '@/components/common/SeverityBadge';
import { useGitHubConfig } from '@/hooks/useGitHub';
import { usePhaseData } from '@/hooks/usePhaseData';
import type {
  Phase01eData,
  Phase02cData,
  Phase03Data,
  Phase04Data,
  Property,
  PropertyWithCode,
  AuditMapItem,
  ReviewedItem,
} from '@/types/pipeline';
import styles from './PropertyPage.module.css';

export function PropertyPage() {
  const { propertyId } = useParams<{ propertyId: string }>();
  const { branch, setBranch } = useGitHubConfig();

  const { data: data01e } = usePhaseData('01e', branch);
  const { data: data02c } = usePhaseData('02c', branch);
  const { data: data03 } = usePhaseData('03', branch);
  const { data: data04 } = usePhaseData('04', branch);

  const prop01e = (data01e as Phase01eData | null)?.properties.find(
    (p) => p.property_id === propertyId,
  );
  const prop02c = (data02c as Phase02cData | null)?.properties_with_code.find(
    (p) => p.property_id === propertyId,
  );
  const prop03 = (data03 as Phase03Data | null)?.audit_items.find(
    (p) => p.property_id === propertyId,
  );
  const prop04 = (data04 as Phase04Data | null)?.reviewed_items.find(
    (p) => p.property_id === propertyId,
  );

  return (
    <div>
      <Header
        branch={branch}
        onBranchChange={setBranch}
        title={`${ja.tracker_title}: ${propertyId}`}
      />
      <div className={styles.content}>
        <Link to="/" className={styles.back}>{ja.back}</Link>

        {/* Phase 01e: Property Definition */}
        <Section title={`01e - ${ja.tracker_phase_01e}`}>
          {prop01e ? <PropertySection prop={prop01e} /> : <NoData />}
        </Section>

        {/* Phase 02c: Code Resolution */}
        <Section title={`02c - ${ja.tracker_phase_02c}`}>
          {prop02c ? <CodeSection prop={prop02c} /> : <NoData />}
        </Section>

        {/* Phase 03: Audit Result */}
        <Section title={`03 - ${ja.tracker_phase_03}`}>
          {prop03 ? <AuditSection item={prop03} /> : <NoData />}
        </Section>

        {/* Phase 04: Review Verdict */}
        <Section title={`04 - ${ja.tracker_phase_04}`}>
          {prop04 ? <ReviewSection item={prop04} /> : <NoData />}
        </Section>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className={styles.section}>
      <h2 className={styles.sectionTitle}>{title}</h2>
      <div className={styles.sectionBody}>{children}</div>
    </section>
  );
}

function NoData() {
  return <p className={styles.noData}>{ja.tracker_not_found}</p>;
}

function PropertySection({ prop }: { prop: Property }) {
  return (
    <div className={styles.grid}>
      <Row label={ja.col_severity}><SeverityBadge severity={prop.severity} /></Row>
      <Row label={ja.col_type}>{prop.type}</Row>
      <Row label={ja.col_covers}><code>{prop.covers}</code></Row>
      <Row label={ja.col_text}>{prop.text}</Row>
      <Row label={ja.col_assertion}><code>{prop.assertion}</code></Row>
      <Row label={ja.col_reachability}>{prop.reachability?.classification ?? '-'}</Row>
      <Row label={ja.col_exploitability}>{prop.exploitability}</Row>
      <Row label={ja.col_bug_bounty}>{prop.bug_bounty_eligible ? ja.yes : ja.no}</Row>
    </div>
  );
}

function CodeSection({ prop }: { prop: PropertyWithCode }) {
  const scope = prop.code_scope;
  return (
    <div className={styles.grid}>
      <Row label={ja.col_resolution}>{scope?.resolution_status ?? '-'}</Row>
      {scope?.locations?.map((loc, i) => (
        <Row key={i} label={`${ja.col_file} (${loc.role})`}>
          <code>{loc.file}:{loc.line_range?.start}-{loc.line_range?.end}</code>
          {loc.symbol && <span className={styles.symbol}>{loc.symbol}</span>}
        </Row>
      ))}
      {prop.code_excerpt && (
        <Row label="コード抜粋">
          <pre className={styles.codeBlock}>{prop.code_excerpt}</pre>
        </Row>
      )}
    </div>
  );
}

function AuditSection({ item }: { item: AuditMapItem }) {
  const trail = item.audit_trail;
  return (
    <div className={styles.grid}>
      <Row label={ja.col_classification}>{item.classification}</Row>
      <Row label={ja.col_summary}>{item.summary ?? '-'}</Row>
      <Row label={ja.col_attack_scenario}>{item.attack_scenario ?? '-'}</Row>
      <Row label={ja.col_bug_bounty}>
        {item.bug_bounty_eligible === true ? ja.yes : item.bug_bounty_eligible === false ? ja.no : '-'}
      </Row>
      {trail && (
        <>
          <Row label={ja.audit_abstract_interpretation}>
            {trail.phase1_abstract_interpretation
              ? JSON.stringify(trail.phase1_abstract_interpretation, null, 2)
              : '-'}
          </Row>
          <Row label={ja.audit_symbolic_execution}>
            {trail.phase2_symbolic_execution
              ? JSON.stringify(trail.phase2_symbolic_execution, null, 2)
              : '-'}
          </Row>
          <Row label={ja.audit_reachability}>
            {trail.phase2_5_reachability_analysis
              ? JSON.stringify(trail.phase2_5_reachability_analysis, null, 2)
              : '-'}
          </Row>
          <Row label={ja.audit_invariant_proving}>
            {trail.phase3_invariant_proving
              ? JSON.stringify(trail.phase3_invariant_proving, null, 2)
              : '-'}
          </Row>
          <Row label={ja.audit_scope_filtering}>
            {trail.phase3_5_scope_filtering
              ? JSON.stringify(trail.phase3_5_scope_filtering, null, 2)
              : '-'}
          </Row>
        </>
      )}
    </div>
  );
}

function ReviewSection({ item }: { item: ReviewedItem }) {
  return (
    <div className={styles.grid}>
      <Row label={ja.col_verdict}>
        <strong>{item.review_verdict}</strong>
      </Row>
      <Row label={ja.col_adjusted_severity}>
        {item.adjusted_severity ? <SeverityBadge severity={item.adjusted_severity} /> : '-'}
      </Row>
      <Row label={ja.col_reviewer_notes}>{item.reviewer_notes ?? '-'}</Row>
      <Row label={ja.col_recommendation}>{item.final_recommendation ?? '-'}</Row>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className={styles.row}>
      <span className={styles.rowLabel}>{label}</span>
      <span className={styles.rowValue}>{children}</span>
    </div>
  );
}
