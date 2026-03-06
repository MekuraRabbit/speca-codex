import { useState, useEffect, useCallback, useRef } from 'react';
import { ja } from '@/i18n/ja';
import { Header } from '@/components/layout/Header';
import { useGitHubConfig } from '@/hooks/useGitHub';
import {
  dispatchPhaseWorkflow,
  fetchLatestPhaseRun,
  fetchWorkflowRunById,
  GitHubApiError,
  PHASE_WORKFLOWS,
  type WorkflowRun,
  type PhaseId,
} from '@/lib/github-client';
import styles from './AuditWizardPage.module.css';

type WizardStep = 'input' | 'confirm' | 'running' | 'done';

const STEPS: { key: WizardStep; label: string }[] = [
  { key: 'input', label: ja.wizard_step_input },
  { key: 'confirm', label: ja.wizard_step_confirm },
  { key: 'running', label: ja.wizard_step_running },
  { key: 'done', label: ja.wizard_step_done },
];

const PHASE_OPTIONS: { id: PhaseId; label: string; desc: string }[] = [
  { id: '01a', label: ja.phase_01a_name, desc: ja.phase_01a_desc },
  { id: '01b', label: ja.phase_01b_name, desc: ja.phase_01b_desc },
  { id: '01e', label: ja.phase_01e_name, desc: ja.phase_01e_desc },
  { id: '02c', label: ja.phase_02c_name, desc: ja.phase_02c_desc },
  { id: '03', label: ja.phase_03_name, desc: ja.phase_03_desc },
  { id: '04', label: ja.phase_04_name, desc: ja.phase_04_desc },
];

function StepIndicator({ current }: { current: WizardStep }) {
  const currentIdx = STEPS.findIndex((s) => s.key === current);
  return (
    <div className={styles.stepIndicator}>
      {STEPS.map((step, i) => (
        <div key={step.key} style={{ display: 'contents' }}>
          {i > 0 && (
            <div
              className={`${styles.stepLine} ${i <= currentIdx ? styles.done : ''}`}
            />
          )}
          <div className={styles.step}>
            <div
              className={`${styles.stepCircle} ${
                i === currentIdx ? styles.active : i < currentIdx ? styles.done : ''
              }`}
            >
              {i < currentIdx ? '\u2713' : i + 1}
            </div>
            <span
              className={`${styles.stepLabel} ${i === currentIdx ? styles.active : ''}`}
            >
              {step.label}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

// --- Phase-specific input helpers ---

/** For 01a-01e, dispatch on master and pass branch as input.
 *  For 02c-04, dispatch ON the branch (ref = branch). */
function getDispatchRef(phaseId: PhaseId, phaseBranch: string): string {
  if (['02c', '03', '04'].includes(phaseId)) return phaseBranch;
  return 'master';
}

function buildPhaseInputs(
  phaseId: PhaseId,
  state: PhaseFormState,
): Record<string, string> {
  const common: Record<string, string> = {};
  if (state.workers !== 4) common.workers = String(state.workers);
  if (state.maxConcurrent !== 64) common.max_concurrent = String(state.maxConcurrent);

  switch (phaseId) {
    case '01a':
      return {
        keywords: state.keywords,
        spec_urls: state.specUrls,
        branch: state.branch,
        append_mode: String(state.appendMode),
      };
    case '01b':
      return {
        branch: state.branch,
        ...common,
        force_execute: String(state.forceExecute),
      };
    case '01e':
      return {
        branch: state.branch,
        ...common,
        force_execute: String(state.forceExecute),
      };
    case '02c':
      return {
        target_repo: state.targetRepo02c,
        target_ref_type: state.targetRefType,
        audit_scope: state.auditScope,
        ...common,
        force_execute: String(state.forceExecute),
      };
    case '03':
      return common;
    case '04':
      return common;
  }
}

interface PhaseFormState {
  branch: string;
  keywords: string;
  specUrls: string;
  appendMode: boolean;
  targetRepo02c: string;
  targetRefType: string;
  auditScope: string;
  forceExecute: boolean;
  workers: number;
  maxConcurrent: number;
}

const INITIAL_PHASE_FORM: PhaseFormState = {
  branch: '',
  keywords: '',
  specUrls: '',
  appendMode: false,
  targetRepo02c: '',
  targetRefType: 'latest_default_branch',
  auditScope: 'auto',
  forceExecute: false,
  workers: 4,
  maxConcurrent: 64,
};

function canSubmitPhase(phaseId: PhaseId, state: PhaseFormState): boolean {
  switch (phaseId) {
    case '01a':
      return state.keywords.trim() !== '' && state.specUrls.trim() !== '';
    case '01b':
    case '01e':
      return state.branch.trim() !== '';
    case '02c':
      return state.targetRepo02c.trim() !== '';
    case '03':
    case '04':
      return state.branch.trim() !== '';
  }
}

// --- Phase-specific input forms ---

function Phase01aInputs({
  state,
  onChange,
}: {
  state: PhaseFormState;
  onChange: (s: Partial<PhaseFormState>) => void;
}) {
  return (
    <>
      <div className={styles.field}>
        <label className={styles.label}>{ja.wizard_phase_branch}</label>
        <p className={styles.desc}>{ja.wizard_phase_branch_desc}</p>
        <input
          type="text"
          className={styles.input}
          value={state.branch}
          onChange={(e) => onChange({ branch: e.target.value })}
          placeholder={ja.wizard_phase_branch_placeholder}
        />
      </div>
      <div className={styles.field}>
        <label className={styles.label}>{ja.wizard_phase_01a_keywords}</label>
        <input
          type="text"
          className={styles.input}
          value={state.keywords}
          onChange={(e) => onChange({ keywords: e.target.value })}
          placeholder={ja.wizard_phase_01a_keywords_placeholder}
        />
      </div>
      <div className={styles.field}>
        <label className={styles.label}>{ja.wizard_phase_01a_spec_urls}</label>
        <input
          type="text"
          className={styles.input}
          value={state.specUrls}
          onChange={(e) => onChange({ specUrls: e.target.value })}
          placeholder={ja.wizard_phase_01a_spec_urls_placeholder}
        />
      </div>
      <div className={styles.checkField}>
        <label>
          <input
            type="checkbox"
            checked={state.appendMode}
            onChange={(e) => onChange({ appendMode: e.target.checked })}
          />
          <span>{ja.wizard_phase_01a_append_mode}</span>
        </label>
      </div>
    </>
  );
}

function PhaseBranchInputs({
  state,
  onChange,
}: {
  state: PhaseFormState;
  onChange: (s: Partial<PhaseFormState>) => void;
}) {
  return (
    <>
      <div className={styles.field}>
        <label className={styles.label}>{ja.wizard_phase_branch}</label>
        <p className={styles.desc}>{ja.wizard_phase_branch_desc}</p>
        <input
          type="text"
          className={styles.input}
          value={state.branch}
          onChange={(e) => onChange({ branch: e.target.value })}
          placeholder={ja.wizard_phase_branch_placeholder}
        />
      </div>
      <div className={styles.checkField}>
        <label>
          <input
            type="checkbox"
            checked={state.forceExecute}
            onChange={(e) => onChange({ forceExecute: e.target.checked })}
          />
          <span>{ja.wizard_phase_force_execute}</span>
        </label>
      </div>
    </>
  );
}

function Phase02cInputs({
  state,
  onChange,
}: {
  state: PhaseFormState;
  onChange: (s: Partial<PhaseFormState>) => void;
}) {
  return (
    <>
      <div className={styles.field}>
        <label className={styles.label}>{ja.wizard_phase_02c_target_repo}</label>
        <input
          type="text"
          className={styles.input}
          value={state.targetRepo02c}
          onChange={(e) => onChange({ targetRepo02c: e.target.value })}
          placeholder={ja.wizard_phase_02c_target_repo_placeholder}
        />
      </div>
      <div className={styles.field}>
        <label className={styles.label}>{ja.wizard_phase_02c_target_ref_type}</label>
        <select
          className={styles.select}
          value={state.targetRefType}
          onChange={(e) => onChange({ targetRefType: e.target.value })}
        >
          <option value="latest_default_branch">{ja.wizard_phase_02c_target_ref_latest}</option>
          <option value="fusaka-audit">{ja.wizard_phase_02c_target_ref_fusaka}</option>
        </select>
      </div>
      <div className={styles.field}>
        <label className={styles.label}>{ja.wizard_phase_02c_audit_scope}</label>
        <select
          className={styles.select}
          value={state.auditScope}
          onChange={(e) => onChange({ auditScope: e.target.value })}
        >
          <option value="auto">auto</option>
          <option value="el">el</option>
          <option value="cl">cl</option>
          <option value="both">both</option>
        </select>
      </div>
      <div className={styles.checkField}>
        <label>
          <input
            type="checkbox"
            checked={state.forceExecute}
            onChange={(e) => onChange({ forceExecute: e.target.checked })}
          />
          <span>{ja.wizard_phase_force_execute}</span>
        </label>
      </div>
    </>
  );
}

function PhaseSpecificInputs({
  phaseId,
  state,
  onChange,
}: {
  phaseId: PhaseId;
  state: PhaseFormState;
  onChange: (s: Partial<PhaseFormState>) => void;
}) {
  switch (phaseId) {
    case '01a':
      return <Phase01aInputs state={state} onChange={onChange} />;
    case '01b':
    case '01e':
      return <PhaseBranchInputs state={state} onChange={onChange} />;
    case '02c':
      return <Phase02cInputs state={state} onChange={onChange} />;
    case '03':
    case '04':
      return (
        <div className={styles.field}>
          <label className={styles.label}>{ja.wizard_phase_branch}</label>
          <p className={styles.desc}>{ja.wizard_phase_branch_desc}</p>
          <input
            type="text"
            className={styles.input}
            value={state.branch}
            onChange={(e) => onChange({ branch: e.target.value })}
            placeholder={ja.wizard_phase_branch_placeholder}
          />
        </div>
      );
  }
}

// --- Confirm card ---

function PhaseConfirmContent({
  phaseId,
  state,
}: {
  phaseId: PhaseId;
  state: PhaseFormState;
}) {
  const phaseOption = PHASE_OPTIONS.find((p) => p.id === phaseId)!;
  const dispatchRef = getDispatchRef(phaseId, state.branch);

  return (
    <div className={styles.confirmCard}>
      <div className={styles.confirmRow}>
        <span className={styles.confirmLabel}>{ja.wizard_phase_select}</span>
        <span className={`${styles.confirmValue} ${styles.confirmCode}`}>
          {phaseId} - {phaseOption.label}
        </span>
      </div>
      <div className={styles.confirmRow}>
        <span className={styles.confirmLabel}>Dispatch Ref</span>
        <span className={`${styles.confirmValue} ${styles.confirmCode}`}>
          {dispatchRef || 'master'}
        </span>
      </div>
      {phaseId === '01a' && (
        <>
          {state.branch && (
            <div className={styles.confirmRow}>
              <span className={styles.confirmLabel}>{ja.wizard_phase_branch}</span>
              <span className={`${styles.confirmValue} ${styles.confirmCode}`}>
                {state.branch}
              </span>
            </div>
          )}
          <div className={styles.confirmRow}>
            <span className={styles.confirmLabel}>{ja.wizard_phase_01a_keywords}</span>
            <span className={styles.confirmValue}>{state.keywords}</span>
          </div>
          <div className={styles.confirmRow}>
            <span className={styles.confirmLabel}>{ja.wizard_phase_01a_spec_urls}</span>
            <span className={styles.confirmValue}>{state.specUrls}</span>
          </div>
          {state.appendMode && (
            <div className={styles.confirmRow}>
              <span className={styles.confirmLabel}>{ja.wizard_phase_01a_append_mode}</span>
              <span className={styles.confirmValue}>{ja.yes}</span>
            </div>
          )}
        </>
      )}
      {(phaseId === '01b' || phaseId === '01e') && (
        <>
          <div className={styles.confirmRow}>
            <span className={styles.confirmLabel}>{ja.wizard_phase_branch}</span>
            <span className={`${styles.confirmValue} ${styles.confirmCode}`}>
              {state.branch}
            </span>
          </div>
          {state.forceExecute && (
            <div className={styles.confirmRow}>
              <span className={styles.confirmLabel}>{ja.wizard_phase_force_execute}</span>
              <span className={styles.confirmValue}>{ja.yes}</span>
            </div>
          )}
        </>
      )}
      {phaseId === '02c' && (
        <>
          <div className={styles.confirmRow}>
            <span className={styles.confirmLabel}>{ja.wizard_phase_02c_target_repo}</span>
            <span className={`${styles.confirmValue} ${styles.confirmCode}`}>
              {state.targetRepo02c}
            </span>
          </div>
          <div className={styles.confirmRow}>
            <span className={styles.confirmLabel}>{ja.wizard_phase_02c_target_ref_type}</span>
            <span className={styles.confirmValue}>{state.targetRefType}</span>
          </div>
          <div className={styles.confirmRow}>
            <span className={styles.confirmLabel}>{ja.wizard_phase_02c_audit_scope}</span>
            <span className={styles.confirmValue}>{state.auditScope}</span>
          </div>
        </>
      )}
      {(phaseId === '03' || phaseId === '04') && (
        <div className={styles.confirmRow}>
          <span className={styles.confirmLabel}>{ja.wizard_phase_branch}</span>
          <span className={`${styles.confirmValue} ${styles.confirmCode}`}>
            {state.branch}
          </span>
        </div>
      )}
      <div className={styles.confirmRow}>
        <span className={styles.confirmLabel}>{ja.wizard_workers}</span>
        <span className={styles.confirmValue}>{state.workers}</span>
      </div>
      <div className={styles.confirmRow}>
        <span className={styles.confirmLabel}>{ja.wizard_max_concurrent}</span>
        <span className={styles.confirmValue}>{state.maxConcurrent}</span>
      </div>
    </div>
  );
}

// ============================================================
// Main component
// ============================================================

export function AuditWizardPage() {
  const { branch, setBranch } = useGitHubConfig();

  // Phase state
  const [selectedPhase, setSelectedPhase] = useState<PhaseId>('01a');
  const [phaseForm, setPhaseForm] = useState<PhaseFormState>(INITIAL_PHASE_FORM);

  const updatePhaseForm = useCallback((partial: Partial<PhaseFormState>) => {
    setPhaseForm((prev) => ({ ...prev, ...partial }));
  }, []);

  // Wizard state
  const [step, setStep] = useState<WizardStep>('input');
  const [error, setError] = useState<string | null>(null);
  const [runId, setRunId] = useState<number | null>(null);
  const [run, setRun] = useState<WorkflowRun | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const dispatchTime = useRef<number>(0);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const elapsedRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const canProceed = canSubmitPhase(selectedPhase, phaseForm);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    if (elapsedRef.current) {
      clearInterval(elapsedRef.current);
      elapsedRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  const handleExecute = async () => {
    setStep('running');
    setError(null);
    setElapsed(0);
    dispatchTime.current = Date.now();

    elapsedRef.current = setInterval(() => {
      setElapsed(Math.floor((Date.now() - dispatchTime.current) / 1000));
    }, 1000);

    try {
      const ref = getDispatchRef(selectedPhase, phaseForm.branch);
      const inputs = buildPhaseInputs(selectedPhase, phaseForm);
      await dispatchPhaseWorkflow(selectedPhase, ref, inputs);
    } catch (err) {
      stopPolling();
      if (err instanceof GitHubApiError && err.status === 403) {
        setError(ja.wizard_token_scope_error);
      } else {
        setError(
          err instanceof Error ? err.message : ja.wizard_dispatch_error,
        );
      }
      setStep('input');
      return;
    }

    // Poll for the run
    let foundRunId: number | null = null;
    const workflowName = PHASE_WORKFLOWS[selectedPhase].workflowName;

    pollRef.current = setInterval(async () => {
      try {
        if (!foundRunId) {
          const latestRun = await fetchLatestPhaseRun(selectedPhase);
          if (latestRun) {
            const createdAt = new Date(latestRun.created_at).getTime();
            if (
              createdAt >= dispatchTime.current - 30000 &&
              latestRun.name === workflowName
            ) {
              foundRunId = latestRun.id;
              setRunId(latestRun.id);
              setRun(latestRun);
            }
          }
        } else {
          const updatedRun = await fetchWorkflowRunById(foundRunId);
          setRun(updatedRun);
          if (updatedRun.status === 'completed') {
            stopPolling();
            setStep('done');
          }
        }
      } catch {
        // Ignore polling errors
      }
    }, 10000);
  };

  const handleReset = () => {
    stopPolling();
    setStep('input');
    setPhaseForm(INITIAL_PHASE_FORM);
    setError(null);
    setRunId(null);
    setRun(null);
    setElapsed(0);
  };

  return (
    <div>
      <Header branch={branch} onBranchChange={setBranch} title={ja.wizard_title} />
      <div className={styles.content}>
        <StepIndicator current={step} />

        {error && <div className={styles.error}>{error}</div>}

        {/* Step 1: Input */}
        {step === 'input' && (
          <>
            <div className={styles.field}>
              <label className={styles.label}>{ja.wizard_phase_select}</label>
              <select
                className={styles.select}
                value={selectedPhase}
                onChange={(e) => {
                  setSelectedPhase(e.target.value as PhaseId);
                  setPhaseForm(INITIAL_PHASE_FORM);
                }}
              >
                {PHASE_OPTIONS.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.id} - {p.label}
                  </option>
                ))}
              </select>
              <p className={styles.desc}>
                {PHASE_OPTIONS.find((p) => p.id === selectedPhase)?.desc}
              </p>
            </div>

            <PhaseSpecificInputs
              phaseId={selectedPhase}
              state={phaseForm}
              onChange={updatePhaseForm}
            />

            {/* Workers / max_concurrent for phases that support them */}
            {selectedPhase !== '01a' && (
              <details className={styles.advancedToggle}>
                <summary>{ja.wizard_advanced}</summary>
                <div className={styles.advancedContent}>
                  <div className={styles.row}>
                    <div className={styles.field}>
                      <label className={styles.label}>{ja.wizard_workers}</label>
                      <input
                        type="number"
                        className={styles.input}
                        value={phaseForm.workers}
                        onChange={(e) =>
                          updatePhaseForm({ workers: Number(e.target.value) })
                        }
                        min={1}
                        max={16}
                      />
                    </div>
                    <div className={styles.field}>
                      <label className={styles.label}>{ja.wizard_max_concurrent}</label>
                      <input
                        type="number"
                        className={styles.input}
                        value={phaseForm.maxConcurrent}
                        onChange={(e) =>
                          updatePhaseForm({ maxConcurrent: Number(e.target.value) })
                        }
                        min={1}
                        max={256}
                      />
                    </div>
                  </div>
                </div>
              </details>
            )}

            <div className={styles.actions}>
              <button
                className={styles.primaryButton}
                disabled={!canProceed}
                onClick={() => {
                  setError(null);
                  setStep('confirm');
                }}
              >
                {ja.wizard_next}
              </button>
            </div>
          </>
        )}

        {/* Step 2: Confirm */}
        {step === 'confirm' && (
          <>
            <h2 className={styles.sectionTitle}>
              {ja.wizard_phase_confirm_title}
            </h2>

            <PhaseConfirmContent phaseId={selectedPhase} state={phaseForm} />

            <div className={styles.actions}>
              <button
                className={styles.secondaryButton}
                onClick={() => setStep('input')}
              >
                {ja.wizard_back}
              </button>
              <button className={styles.primaryButton} onClick={handleExecute}>
                {ja.wizard_execute}
              </button>
            </div>
          </>
        )}

        {/* Step 3: Running */}
        {step === 'running' && (
          <div className={styles.progressCard}>
            <div className={styles.spinner} />
            <div className={styles.progressStatus}>
              {!runId ? ja.wizard_phase_dispatching : ja.wizard_polling}
            </div>
            {run && (
              <div className={styles.progressSub}>
                {ja.wizard_run_status}: {run.status}
                {run.conclusion && ` (${run.conclusion})`}
              </div>
            )}
            <div className={styles.progressSub}>
              {ja.wizard_elapsed}: {formatElapsed(elapsed)}
            </div>
            {run && (
              <a
                className={styles.runLink}
                href={run.html_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                {ja.wizard_view_actions}
              </a>
            )}
          </div>
        )}

        {/* Step 4: Done */}
        {step === 'done' && run && (
          <div
            className={`${styles.doneCard} ${
              run.conclusion !== 'success' ? styles.failed : ''
            }`}
          >
            <div className={styles.doneTitle}>
              {run.conclusion === 'success'
                ? ja.wizard_phase_completed
                : ja.wizard_phase_failed}
            </div>
            <div className={styles.progressSub}>
              {ja.wizard_elapsed}: {formatElapsed(elapsed)}
            </div>
            <div className={styles.doneActions}>
              {run.conclusion === 'success' && run.head_branch && (
                <button
                  className={styles.primaryButton}
                  onClick={() => {
                    setBranch(run.head_branch);
                    window.location.href = '/';
                  }}
                >
                  {ja.wizard_view_dashboard}
                </button>
              )}
              <a
                className={styles.secondaryButton}
                href={run.html_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{ textDecoration: 'none' }}
              >
                {ja.wizard_view_actions}
              </a>
              <button className={styles.secondaryButton} onClick={handleReset}>
                {ja.wizard_start_new}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
