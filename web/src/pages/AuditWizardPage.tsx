import { useState, useEffect, useCallback, useRef } from 'react';
import { ja } from '@/i18n/ja';
import { Header } from '@/components/layout/Header';
import { useGitHubConfig } from '@/hooks/useGitHub';
import {
  dispatchPhase,
  cancelRun,
  subscribeToProgress,
  type PhaseId,
  type ProgressEvent,
} from '@/lib/api-client';
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

// --- Phase-specific types ---

interface PhaseFormState {
  keywords: string;
  specUrls: string;
  appendMode: boolean;
  targetRepo02c: string;
  targetRefType: string;
  auditScope: string;
  forceExecute: boolean;
  workers: number;
  maxConcurrent: number;
  minSeverity: string;
}

const INITIAL_PHASE_FORM: PhaseFormState = {
  keywords: '',
  specUrls: '',
  appendMode: false,
  targetRepo02c: '',
  targetRefType: 'latest_default_branch',
  auditScope: 'auto',
  forceExecute: false,
  workers: 4,
  maxConcurrent: 8,
  minSeverity: '',
};

interface ProgressState {
  totalItems: number;
  completedItems: number;
  failedBatches: number;
  costUsd: number;
  budgetPct: number;
  totalResults: number;
}

const INITIAL_PROGRESS: ProgressState = {
  totalItems: 0,
  completedItems: 0,
  failedBatches: 0,
  costUsd: 0,
  budgetPct: 0,
  totalResults: 0,
};

function canSubmitPhase(phaseId: PhaseId, state: PhaseFormState): boolean {
  switch (phaseId) {
    case '01a':
      return state.keywords.trim() !== '' && state.specUrls.trim() !== '';
    case '02c':
      return state.targetRepo02c.trim() !== '';
    case '01b':
    case '01e':
    case '03':
    case '04':
      return true;
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

function PhaseCommonInputs({
  state,
  onChange,
}: {
  state: PhaseFormState;
  onChange: (s: Partial<PhaseFormState>) => void;
}) {
  return (
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
    case '02c':
      return <Phase02cInputs state={state} onChange={onChange} />;
    case '01b':
    case '01e':
    case '03':
    case '04':
      return <PhaseCommonInputs state={state} onChange={onChange} />;
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

  return (
    <div className={styles.confirmCard}>
      <div className={styles.confirmRow}>
        <span className={styles.confirmLabel}>{ja.wizard_phase_select}</span>
        <span className={`${styles.confirmValue} ${styles.confirmCode}`}>
          {phaseId} - {phaseOption.label}
        </span>
      </div>
      {phaseId === '01a' && (
        <>
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
      {state.forceExecute && (
        <div className={styles.confirmRow}>
          <span className={styles.confirmLabel}>{ja.wizard_phase_force_execute}</span>
          <span className={styles.confirmValue}>{ja.yes}</span>
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
  const [runId, setRunId] = useState<string | null>(null);
  const [progress, setProgress] = useState<ProgressState>(INITIAL_PROGRESS);
  const [elapsed, setElapsed] = useState(0);
  const [runStatus, setRunStatus] = useState<string>('');
  const dispatchTime = useRef<number>(0);
  const elapsedRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const unsubRef = useRef<(() => void) | null>(null);

  const canProceed = canSubmitPhase(selectedPhase, phaseForm);

  const cleanup = useCallback(() => {
    if (elapsedRef.current) {
      clearInterval(elapsedRef.current);
      elapsedRef.current = null;
    }
    if (unsubRef.current) {
      unsubRef.current();
      unsubRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => cleanup();
  }, [cleanup]);

  const handleSSEEvent = useCallback((event: ProgressEvent) => {
    const d = event.data;
    switch (event.type) {
      case 'phase_start':
        setRunStatus(String(d.phase_id ?? ''));
        break;
      case 'items_loaded':
        setProgress((p) => ({
          ...p,
          totalItems: Number(d.total_items ?? p.totalItems),
        }));
        break;
      case 'batch_complete':
        setProgress((p) => ({
          ...p,
          completedItems: Number(d.completed ?? p.completedItems),
          totalResults: Number(d.results_count ?? 0) + p.totalResults,
        }));
        break;
      case 'batch_failed':
        setProgress((p) => ({
          ...p,
          failedBatches: p.failedBatches + 1,
          completedItems: Number(d.completed ?? p.completedItems),
        }));
        break;
      case 'cost_update':
        setProgress((p) => ({
          ...p,
          costUsd: Number(d.total_cost_usd ?? p.costUsd),
          budgetPct: Number(d.budget_utilization_pct ?? p.budgetPct),
        }));
        break;
      case 'phase_complete':
        setProgress((p) => ({
          ...p,
          totalResults: Number(d.total_results ?? p.totalResults),
        }));
        cleanup();
        setStep('done');
        setRunStatus('completed');
        break;
      case 'phase_error':
        cleanup();
        setError(String(d.error ?? ja.wizard_dispatch_error));
        setStep('done');
        setRunStatus('failed');
        break;
    }
  }, [cleanup]);

  const handleExecute = async () => {
    setStep('running');
    setError(null);
    setElapsed(0);
    setProgress(INITIAL_PROGRESS);
    setRunStatus('dispatching');
    dispatchTime.current = Date.now();

    elapsedRef.current = setInterval(() => {
      setElapsed(Math.floor((Date.now() - dispatchTime.current) / 1000));
    }, 1000);

    try {
      const res = await dispatchPhase({
        phase_id: selectedPhase,
        workers: phaseForm.workers,
        max_concurrent: phaseForm.maxConcurrent,
        force: phaseForm.forceExecute,
        keywords: selectedPhase === '01a' ? phaseForm.keywords : undefined,
        spec_urls: selectedPhase === '01a' ? phaseForm.specUrls : undefined,
        target_repo: selectedPhase === '02c' ? phaseForm.targetRepo02c : undefined,
        target_ref_type: selectedPhase === '02c' ? phaseForm.targetRefType : undefined,
        audit_scope: selectedPhase === '02c' ? phaseForm.auditScope : undefined,
        min_severity: phaseForm.minSeverity || undefined,
      });

      setRunId(res.run_id);
      setRunStatus('running');

      // Subscribe to SSE progress
      unsubRef.current = subscribeToProgress(
        res.run_id,
        handleSSEEvent,
        () => {
          // SSE done
          cleanup();
          setStep('done');
        },
        (err) => {
          cleanup();
          setError(err.message);
          setStep('done');
          setRunStatus('failed');
        },
      );
    } catch (err) {
      cleanup();
      setError(err instanceof Error ? err.message : ja.wizard_dispatch_error);
      setStep('input');
    }
  };

  const handleCancel = async () => {
    if (runId) {
      try {
        await cancelRun(runId);
      } catch {
        // Ignore cancel errors
      }
    }
    cleanup();
    setStep('done');
    setRunStatus('cancelled');
  };

  const handleReset = () => {
    cleanup();
    setStep('input');
    setPhaseForm(INITIAL_PHASE_FORM);
    setError(null);
    setRunId(null);
    setProgress(INITIAL_PROGRESS);
    setElapsed(0);
    setRunStatus('');
  };

  const progressPct =
    progress.totalItems > 0
      ? Math.round((progress.completedItems / progress.totalItems) * 100)
      : 0;

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
              {runStatus === 'dispatching'
                ? ja.wizard_phase_dispatching
                : ja.wizard_polling}
            </div>

            {progress.totalItems > 0 && (
              <div className={styles.progressBarWrap}>
                <div className={styles.progressBarTrack}>
                  <div
                    className={styles.progressBarFill}
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
                <div className={styles.progressBarLabel}>
                  {ja.wizard_batch_progress}: {progress.completedItems}/{progress.totalItems} ({progressPct}%)
                </div>
              </div>
            )}

            {progress.costUsd > 0 && (
              <div className={styles.progressSub}>
                {ja.wizard_cost_display}: ${progress.costUsd.toFixed(2)}
              </div>
            )}

            {progress.failedBatches > 0 && (
              <div className={styles.progressSub}>
                {ja.wizard_batches} ({ja.status_failed}): {progress.failedBatches}
              </div>
            )}

            <div className={styles.progressSub}>
              {ja.wizard_elapsed}: {formatElapsed(elapsed)}
            </div>

            <div className={styles.actions} style={{ justifyContent: 'center' }}>
              <button className={styles.secondaryButton} onClick={handleCancel}>
                {ja.wizard_cancel}
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Done */}
        {step === 'done' && (
          <div
            className={`${styles.doneCard} ${
              runStatus === 'failed' || runStatus === 'cancelled' ? styles.failed : ''
            }`}
          >
            <div className={styles.doneTitle}>
              {runStatus === 'completed'
                ? ja.wizard_phase_completed
                : runStatus === 'cancelled'
                  ? ja.wizard_cancel
                  : ja.wizard_phase_failed}
            </div>

            {progress.totalResults > 0 && (
              <div className={styles.progressSub}>
                {ja.dashboard_total_findings}: {progress.totalResults}
              </div>
            )}

            {progress.costUsd > 0 && (
              <div className={styles.progressSub}>
                {ja.wizard_cost_display}: ${progress.costUsd.toFixed(2)}
              </div>
            )}

            <div className={styles.progressSub}>
              {ja.wizard_elapsed}: {formatElapsed(elapsed)}
            </div>

            <div className={styles.doneActions}>
              {runStatus === 'completed' && (
                <button
                  className={styles.primaryButton}
                  onClick={() => {
                    window.location.href = '/';
                  }}
                >
                  {ja.wizard_view_dashboard}
                </button>
              )}
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
