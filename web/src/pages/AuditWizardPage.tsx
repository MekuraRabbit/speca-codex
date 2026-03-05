import { useState, useEffect, useCallback, useRef } from 'react';
import { ja } from '@/i18n/ja';
import { Header } from '@/components/layout/Header';
import { useGitHubConfig } from '@/hooks/useGitHub';
import {
  dispatchWorkflow,
  fetchLatestDispatchRun,
  fetchWorkflowRunById,
  GitHubApiError,
  type WorkflowDispatchInputs,
  type WorkflowRun,
} from '@/lib/github-client';
import styles from './AuditWizardPage.module.css';

type WizardStep = 'input' | 'confirm' | 'running' | 'done';

const STEPS: { key: WizardStep; label: string }[] = [
  { key: 'input', label: ja.wizard_step_input },
  { key: 'confirm', label: ja.wizard_step_confirm },
  { key: 'running', label: ja.wizard_step_running },
  { key: 'done', label: ja.wizard_step_done },
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

export function AuditWizardPage() {
  const { branch, setBranch } = useGitHubConfig();

  // Form state
  const [bugBountyUrl, setBugBountyUrl] = useState('');
  const [targetRepo, setTargetRepo] = useState('');
  const [targetRef, setTargetRef] = useState('');
  const [contractAddresses, setContractAddresses] = useState('');
  const [specUrls, setSpecUrls] = useState('');
  const [keywords, setKeywords] = useState('');
  const [workers, setWorkers] = useState(4);
  const [maxConcurrent, setMaxConcurrent] = useState(64);

  // Wizard state
  const [step, setStep] = useState<WizardStep>('input');
  const [error, setError] = useState<string | null>(null);
  const [runId, setRunId] = useState<number | null>(null);
  const [run, setRun] = useState<WorkflowRun | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const dispatchTime = useRef<number>(0);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const elapsedRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const canProceed = bugBountyUrl.trim() !== '' && targetRepo.trim() !== '';

  const inputs: WorkflowDispatchInputs = {
    bug_bounty_url: bugBountyUrl.trim(),
    target_repo: targetRepo.trim(),
    target_ref: targetRef.trim() || undefined,
    contract_addresses: contractAddresses.trim() || undefined,
    spec_urls: specUrls.trim() || undefined,
    keywords: keywords.trim() || undefined,
    workers,
    max_concurrent: maxConcurrent,
  };

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

    // Start elapsed timer
    elapsedRef.current = setInterval(() => {
      setElapsed(Math.floor((Date.now() - dispatchTime.current) / 1000));
    }, 1000);

    try {
      await dispatchWorkflow('master', inputs);
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

    pollRef.current = setInterval(async () => {
      try {
        if (!foundRunId) {
          // Find the run created after dispatch
          const latestRun = await fetchLatestDispatchRun();
          if (latestRun) {
            const createdAt = new Date(latestRun.created_at).getTime();
            if (
              createdAt >= dispatchTime.current - 30000 &&
              latestRun.name.includes('Full Audit')
            ) {
              foundRunId = latestRun.id;
              setRunId(latestRun.id);
              setRun(latestRun);
            }
          }
        } else {
          // Poll the specific run
          const updatedRun = await fetchWorkflowRunById(foundRunId);
          setRun(updatedRun);
          if (updatedRun.status === 'completed') {
            stopPolling();
            setStep('done');
          }
        }
      } catch {
        // Ignore polling errors, keep trying
      }
    }, 10000);
  };

  const handleReset = () => {
    stopPolling();
    setStep('input');
    setBugBountyUrl('');
    setTargetRepo('');
    setTargetRef('');
    setContractAddresses('');
    setSpecUrls('');
    setKeywords('');
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
              <label className={styles.label}>{ja.wizard_bug_bounty_url}</label>
              <p className={styles.desc}>{ja.wizard_bug_bounty_url_desc}</p>
              <input
                type="url"
                className={styles.input}
                value={bugBountyUrl}
                onChange={(e) => setBugBountyUrl(e.target.value)}
                placeholder={ja.wizard_bug_bounty_url_placeholder}
              />
            </div>

            <div className={styles.field}>
              <label className={styles.label}>{ja.wizard_target_repo}</label>
              <p className={styles.desc}>{ja.wizard_target_repo_desc}</p>
              <input
                type="text"
                className={styles.input}
                value={targetRepo}
                onChange={(e) => setTargetRepo(e.target.value)}
                placeholder={ja.wizard_target_repo_placeholder}
              />
            </div>

            <details className={styles.advancedToggle}>
              <summary>{ja.wizard_advanced}</summary>
              <div className={styles.advancedContent}>
                <div className={styles.field}>
                  <label className={styles.label}>{ja.wizard_target_ref}</label>
                  <p className={styles.desc}>{ja.wizard_target_ref_desc}</p>
                  <input
                    type="text"
                    className={styles.input}
                    value={targetRef}
                    onChange={(e) => setTargetRef(e.target.value)}
                    placeholder={ja.wizard_target_ref_placeholder}
                  />
                </div>

                <div className={styles.field}>
                  <label className={styles.label}>{ja.wizard_contract_addresses}</label>
                  <p className={styles.desc}>{ja.wizard_contract_addresses_desc}</p>
                  <textarea
                    className={styles.textarea}
                    value={contractAddresses}
                    onChange={(e) => setContractAddresses(e.target.value)}
                    placeholder={ja.wizard_contract_addresses_placeholder}
                    rows={4}
                  />
                </div>

                <div className={styles.field}>
                  <label className={styles.label}>{ja.wizard_spec_urls}</label>
                  <input
                    type="text"
                    className={styles.input}
                    value={specUrls}
                    onChange={(e) => setSpecUrls(e.target.value)}
                    placeholder="https://..."
                  />
                </div>

                <div className={styles.field}>
                  <label className={styles.label}>{ja.wizard_keywords}</label>
                  <input
                    type="text"
                    className={styles.input}
                    value={keywords}
                    onChange={(e) => setKeywords(e.target.value)}
                    placeholder="geth,ethereum,EIP,..."
                  />
                </div>

                <div className={styles.row}>
                  <div className={styles.field}>
                    <label className={styles.label}>{ja.wizard_workers}</label>
                    <input
                      type="number"
                      className={styles.input}
                      value={workers}
                      onChange={(e) => setWorkers(Number(e.target.value))}
                      min={1}
                      max={16}
                    />
                  </div>
                  <div className={styles.field}>
                    <label className={styles.label}>{ja.wizard_max_concurrent}</label>
                    <input
                      type="number"
                      className={styles.input}
                      value={maxConcurrent}
                      onChange={(e) => setMaxConcurrent(Number(e.target.value))}
                      min={1}
                      max={256}
                    />
                  </div>
                </div>
              </div>
            </details>

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
            <h2 className={styles.sectionTitle}>{ja.wizard_confirm_title}</h2>
            <div className={styles.confirmCard}>
              <div className={styles.confirmRow}>
                <span className={styles.confirmLabel}>{ja.wizard_bug_bounty_url}</span>
                <span className={styles.confirmValue}>{inputs.bug_bounty_url}</span>
              </div>
              <div className={styles.confirmRow}>
                <span className={styles.confirmLabel}>{ja.wizard_target_repo}</span>
                <span className={`${styles.confirmValue} ${styles.confirmCode}`}>
                  {inputs.target_repo}
                </span>
              </div>
              {inputs.target_ref && (
                <div className={styles.confirmRow}>
                  <span className={styles.confirmLabel}>{ja.wizard_target_ref}</span>
                  <span className={`${styles.confirmValue} ${styles.confirmCode}`}>
                    {inputs.target_ref}
                  </span>
                </div>
              )}
              {inputs.contract_addresses && (
                <div className={styles.confirmRow}>
                  <span className={styles.confirmLabel}>{ja.wizard_contract_addresses}</span>
                  <span className={styles.confirmValue} style={{ whiteSpace: 'pre-wrap', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)' }}>
                    {inputs.contract_addresses}
                  </span>
                </div>
              )}
              {inputs.spec_urls && (
                <div className={styles.confirmRow}>
                  <span className={styles.confirmLabel}>{ja.wizard_spec_urls}</span>
                  <span className={styles.confirmValue}>{inputs.spec_urls}</span>
                </div>
              )}
              {inputs.keywords && (
                <div className={styles.confirmRow}>
                  <span className={styles.confirmLabel}>{ja.wizard_keywords}</span>
                  <span className={styles.confirmValue}>{inputs.keywords}</span>
                </div>
              )}
              <div className={styles.confirmRow}>
                <span className={styles.confirmLabel}>{ja.wizard_workers}</span>
                <span className={styles.confirmValue}>{inputs.workers}</span>
              </div>
              <div className={styles.confirmRow}>
                <span className={styles.confirmLabel}>{ja.wizard_max_concurrent}</span>
                <span className={styles.confirmValue}>{inputs.max_concurrent}</span>
              </div>
            </div>

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
              {!runId ? ja.wizard_waiting_run : ja.wizard_polling}
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
                ? ja.wizard_run_completed
                : ja.wizard_run_failed}
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
