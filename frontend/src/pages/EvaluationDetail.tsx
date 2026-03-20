import axios from 'axios';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';

import { EvidenceCard } from '../components/evaluation/EvidenceCard';
import { FileList } from '../components/evaluation/FileList';
import { FileUploadPanel } from '../components/evaluation/FileUploadPanel';
import { StatusIndicator } from '../components/evaluation/StatusIndicator';
import { CalibrationCompareTable } from '../components/review/CalibrationCompareTable';
import { DimensionScoreEditor, type DimensionScoreDraft } from '../components/review/DimensionScoreEditor';
import { ReviewPanel } from '../components/review/ReviewPanel';
import { fetchCycles } from '../services/cycleService';
import { confirmEvaluation, fetchEvaluationBySubmission, generateEvaluation, submitManualReview } from '../services/evaluationService';
import { fetchSubmissionEvidence, fetchSubmissionFiles, parseFile, uploadSubmissionFiles } from '../services/fileService';
import { fetchEmployee } from '../services/employeeService';
import { recommendSalary } from '../services/salaryService';
import { ensureSubmission } from '../services/submissionService';
import type { CycleRecord, EmployeeRecord, EvaluationRecord, EvidenceRecord, SalaryRecommendationRecord, SubmissionRecord, UploadedFileRecord } from '../types/api';

const FLOW = ['collecting', 'submitted', 'parsing', 'evaluated', 'reviewing', 'calibrated', 'approved', 'published'];

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (error.response?.data as { detail?: string; message?: string } | undefined)?.detail ??
      (error.response?.data as { detail?: string; message?: string } | undefined)?.message ??
      'Failed to load employee detail.';
  }
  return 'Failed to load employee detail.';
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

function createInitialDimensions(): DimensionScoreDraft[] {
  return [
    { code: 'TOOL', label: 'AI tool mastery', score: 70, rationale: 'Awaiting evaluation.' },
    { code: 'DEPTH', label: 'AI application depth', score: 70, rationale: 'Awaiting evaluation.' },
    { code: 'LEARN', label: 'AI learning velocity', score: 70, rationale: 'Awaiting evaluation.' },
    { code: 'SHARE', label: 'Knowledge sharing', score: 70, rationale: 'Awaiting evaluation.' },
    { code: 'IMPACT', label: 'Business impact', score: 70, rationale: 'Awaiting evaluation.' },
  ];
}

function formatDimensionLabel(code: string): string {
  return {
    TOOL: 'AI tool mastery',
    DEPTH: 'AI application depth',
    LEARN: 'AI learning velocity',
    SHARE: 'Knowledge sharing',
    IMPACT: 'Business impact',
  }[code] ?? code;
}

function mapEvaluationToDrafts(evaluation: EvaluationRecord | null): DimensionScoreDraft[] {
  if (!evaluation) {
    return createInitialDimensions();
  }
  return evaluation.dimension_scores.map((dimension) => ({
    code: dimension.dimension_code,
    label: formatDimensionLabel(dimension.dimension_code),
    score: dimension.raw_score,
    rationale: dimension.rationale,
  }));
}

function mapEvidence(item: EvidenceRecord): EvidenceRecord {
  const tags = Object.entries(item.metadata_json ?? {}).map(([key, value]) => `${key}:${String(value)}`);
  return { ...item, tags };
}

function inferStatus(submission: SubmissionRecord | null, files: UploadedFileRecord[], evaluation: EvaluationRecord | null, recommendation: SalaryRecommendationRecord | null): string {
  if (recommendation?.status === 'locked') {
    return 'approved';
  }
  if (evaluation?.status === 'confirmed') {
    return 'calibrated';
  }
  if (evaluation?.status === 'reviewed') {
    return 'reviewing';
  }
  if (evaluation) {
    return 'evaluated';
  }
  if (files.some((file) => file.parse_status === 'parsing')) {
    return 'parsing';
  }
  if (files.some((file) => file.parse_status === 'parsed')) {
    return 'submitted';
  }
  return submission?.status ?? 'collecting';
}

export function EvaluationDetailPage() {
  const { employeeId } = useParams<{ employeeId: string }>();
  const [searchParams] = useSearchParams();
  const [employee, setEmployee] = useState<EmployeeRecord | null>(null);
  const [cycles, setCycles] = useState<CycleRecord[]>([]);
  const [selectedCycleId, setSelectedCycleId] = useState('');
  const [submission, setSubmission] = useState<SubmissionRecord | null>(null);
  const [files, setFiles] = useState<UploadedFileRecord[]>([]);
  const [evidenceItems, setEvidenceItems] = useState<EvidenceRecord[]>([]);
  const [evaluation, setEvaluation] = useState<EvaluationRecord | null>(null);
  const [salaryRecommendation, setSalaryRecommendation] = useState<SalaryRecommendationRecord | null>(null);
  const [dimensions, setDimensions] = useState<DimensionScoreDraft[]>(() => createInitialDimensions());
  const [reviewLevel, setReviewLevel] = useState('Level 3');
  const [reviewComment, setReviewComment] = useState('Manual review opened. Capture disagreements and rationale here before calibration.');
  const [isUploading, setIsUploading] = useState(false);
  const [isReviewSubmitting, setIsReviewSubmitting] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [isGeneratingEvaluation, setIsGeneratingEvaluation] = useState(false);
  const [isGeneratingSalary, setIsGeneratingSalary] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadBase() {
      if (!employeeId) {
        setErrorMessage('Missing employee id.');
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      setErrorMessage(null);
      try {
        const [employeeResponse, cycleResponse] = await Promise.all([fetchEmployee(employeeId), fetchCycles()]);
        if (cancelled) {
          return;
        }
        setEmployee(employeeResponse);
        setCycles(cycleResponse.items);
        const requestedCycleId = searchParams.get('cycleId');
        const fallbackCycleId = cycleResponse.items[0]?.id ?? '';
        setSelectedCycleId(requestedCycleId && cycleResponse.items.some((cycle) => cycle.id === requestedCycleId) ? requestedCycleId : fallbackCycleId);
      } catch (error) {
        if (!cancelled) {
          setErrorMessage(resolveError(error));
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadBase();
    return () => {
      cancelled = true;
    };
  }, [employeeId, searchParams]);

  useEffect(() => {
    let cancelled = false;

    async function loadSubmissionData() {
      if (!employeeId || !selectedCycleId) {
        return;
      }
      try {
        const submissionResponse = await ensureSubmission(employeeId, selectedCycleId);
        if (cancelled) {
          return;
        }
        setSubmission(submissionResponse);

        const [filesResponse, evidenceResponse] = await Promise.all([
          fetchSubmissionFiles(submissionResponse.id),
          fetchSubmissionEvidence(submissionResponse.id),
        ]);
        if (cancelled) {
          return;
        }
        setFiles(filesResponse.items);
        setEvidenceItems(evidenceResponse.items.map(mapEvidence));

        try {
          const evaluationResponse = await fetchEvaluationBySubmission(submissionResponse.id);
          if (!cancelled) {
            setEvaluation(evaluationResponse);
            setDimensions(mapEvaluationToDrafts(evaluationResponse));
            setReviewLevel(evaluationResponse.ai_level);
            setReviewComment(evaluationResponse.explanation);
          }
        } catch {
          if (!cancelled) {
            setEvaluation(null);
            setDimensions(createInitialDimensions());
          }
        }
      } catch (error) {
        if (!cancelled) {
          setErrorMessage(resolveError(error));
        }
      }
    }

    void loadSubmissionData();
    return () => {
      cancelled = true;
    };
  }, [employeeId, selectedCycleId]);

  const currentCycle = useMemo(() => cycles.find((cycle) => cycle.id === selectedCycleId) ?? null, [cycles, selectedCycleId]);
  const currentStatus = useMemo(() => inferStatus(submission, files, evaluation, salaryRecommendation), [submission, files, evaluation, salaryRecommendation]);
  const activeIndex = FLOW.indexOf(currentStatus);
  const calibrationRows = useMemo(
    () => dimensions.map((dimension, index) => ({
      code: dimension.code,
      label: dimension.label,
      aiScore: evaluation?.dimension_scores[index]?.raw_score ?? dimension.score,
      manualScore: dimension.score,
      note: dimension.rationale,
    })),
    [dimensions, evaluation],
  );

  async function refreshSubmissionData(targetSubmissionId: string) {
    const [filesResponse, evidenceResponse] = await Promise.all([
      fetchSubmissionFiles(targetSubmissionId),
      fetchSubmissionEvidence(targetSubmissionId),
    ]);
    setFiles(filesResponse.items);
    setEvidenceItems(evidenceResponse.items.map(mapEvidence));
    try {
      const evaluationResponse = await fetchEvaluationBySubmission(targetSubmissionId);
      setEvaluation(evaluationResponse);
      setDimensions(mapEvaluationToDrafts(evaluationResponse));
      setReviewLevel(evaluationResponse.ai_level);
      setReviewComment(evaluationResponse.explanation);
    } catch {
      setEvaluation(null);
      setDimensions(createInitialDimensions());
    }
  }

  async function handleFilesSelected(selectedFiles: FileList | null) {
    if (!selectedFiles?.length || !submission) {
      return;
    }
    setIsUploading(true);
    try {
      await uploadSubmissionFiles(submission.id, Array.from(selectedFiles));
      await refreshSubmissionData(submission.id);
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsUploading(false);
    }
  }

  async function handleRetryParse(fileId: string) {
    if (!submission) {
      return;
    }
    try {
      await parseFile(fileId);
      await refreshSubmissionData(submission.id);
    } catch (error) {
      setErrorMessage(resolveError(error));
    }
  }

  function handleDeleteFile(fileId: string) {
    setFiles((current) => current.filter((file) => file.id !== fileId));
  }

  async function handleGenerateEvaluation() {
    if (!submission) {
      return;
    }
    setIsGeneratingEvaluation(true);
    try {
      const nextEvaluation = await generateEvaluation(submission.id);
      setEvaluation(nextEvaluation);
      setDimensions(mapEvaluationToDrafts(nextEvaluation));
      setReviewLevel(nextEvaluation.ai_level);
      setReviewComment(nextEvaluation.explanation);
      await refreshSubmissionData(submission.id);
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsGeneratingEvaluation(false);
    }
  }

  async function handleSubmitReview() {
    if (!evaluation) {
      return;
    }
    setIsReviewSubmitting(true);
    try {
      const reviewed = await submitManualReview(evaluation.id, {
        ai_level: reviewLevel,
        explanation: reviewComment,
        dimension_scores: dimensions.map((dimension) => ({
          dimension_code: dimension.code,
          raw_score: dimension.score,
          rationale: dimension.rationale,
        })),
      });
      setEvaluation(reviewed);
      setDimensions(mapEvaluationToDrafts(reviewed));
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsReviewSubmitting(false);
    }
  }

  async function handleConfirmEvaluation() {
    if (!evaluation || !submission) {
      return;
    }
    setIsConfirming(true);
    try {
      await confirmEvaluation(evaluation.id);
      await refreshSubmissionData(submission.id);
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsConfirming(false);
    }
  }

  async function handleGenerateSalary() {
    if (!evaluation) {
      return;
    }
    setIsGeneratingSalary(true);
    try {
      const recommendation = await recommendSalary(evaluation.id);
      setSalaryRecommendation(recommendation);
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsGeneratingSalary(false);
    }
  }

  return (
    <main className="min-h-screen bg-sand px-6 py-10 text-ink">
      <div className="mx-auto flex max-w-6xl flex-col gap-6">
        <header className="rounded-[28px] bg-white p-6 shadow-panel">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-sm uppercase tracking-[0.3em] text-ember">Evaluation Detail</p>
              <h1 className="mt-2 text-3xl font-bold">Employee Evaluation Detail</h1>
              <p className="mt-2 text-sm text-slate-500">This page now reads real submissions, files, evidence, evaluation output, and salary recommendations from the backend.</p>
            </div>
            <div className="flex gap-3">
              <Link className="rounded-full border border-ink/15 px-5 py-3 text-sm font-semibold text-ink" to="/employees">
                Back to list
              </Link>
              <Link className="rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white" to="/cycles/create">
                Create cycle
              </Link>
            </div>
          </div>
        </header>

        {isLoading ? <p className="text-sm text-slate-500">Loading employee detail...</p> : null}
        {errorMessage ? <p className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-600">{errorMessage}</p> : null}

        {employee ? (
          <>
            <section className="grid gap-6 lg:grid-cols-[1.35fr_0.95fr]">
              <article className="rounded-[28px] bg-white p-6 shadow-panel">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <div className="flex flex-wrap items-center gap-3">
                      <h2 className="text-2xl font-bold">{employee.name}</h2>
                      <StatusIndicator status={employee.status} />
                    </div>
                    <p className="mt-2 text-sm text-slate-500">Employee No. {employee.employee_no}</p>
                  </div>
                  <div className="rounded-[24px] bg-slate-50 px-4 py-3 text-right text-sm text-slate-600">
                    <p>Updated at</p>
                    <p className="mt-1 font-semibold text-ink">{formatDateTime(employee.updated_at)}</p>
                  </div>
                </div>

                <dl className="mt-6 grid gap-4 md:grid-cols-2">
                  <div className="rounded-[24px] bg-slate-50 p-4">
                    <dt className="text-sm text-slate-500">Department</dt>
                    <dd className="mt-2 text-lg font-semibold">{employee.department}</dd>
                  </div>
                  <div className="rounded-[24px] bg-slate-50 p-4">
                    <dt className="text-sm text-slate-500">Job family</dt>
                    <dd className="mt-2 text-lg font-semibold">{employee.job_family}</dd>
                  </div>
                  <div className="rounded-[24px] bg-slate-50 p-4">
                    <dt className="text-sm text-slate-500">Job level</dt>
                    <dd className="mt-2 text-lg font-semibold">{employee.job_level}</dd>
                  </div>
                  <label className="rounded-[24px] bg-slate-50 p-4">
                    <span className="text-sm text-slate-500">Current cycle</span>
                    <select className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-ink" onChange={(event) => setSelectedCycleId(event.target.value)} value={selectedCycleId}>
                      {cycles.map((cycle) => (
                        <option key={cycle.id} value={cycle.id}>{cycle.name}</option>
                      ))}
                    </select>
                  </label>
                </dl>
              </article>

              <aside className="rounded-[28px] bg-white p-6 shadow-panel">
                <p className="text-sm uppercase tracking-[0.24em] text-ember">Live Actions</p>
                <div className="mt-4 grid gap-3">
                  <button className="rounded-[24px] border border-slate-200 p-4 text-left disabled:opacity-60" disabled={isGeneratingEvaluation || !submission} onClick={handleGenerateEvaluation} type="button">
                    <h3 className="font-semibold">{isGeneratingEvaluation ? 'Generating evaluation...' : 'Generate AI evaluation'}</h3>
                    <p className="mt-2 text-sm leading-6 text-slate-500">Create or refresh the backend evaluation result for the active submission.</p>
                  </button>
                  <button className="rounded-[24px] border border-slate-200 p-4 text-left disabled:opacity-60" disabled={isGeneratingSalary || !evaluation} onClick={handleGenerateSalary} type="button">
                    <h3 className="font-semibold">{isGeneratingSalary ? 'Generating salary...' : 'Generate salary advice'}</h3>
                    <p className="mt-2 text-sm leading-6 text-slate-500">Run the salary recommendation engine against the current evaluation.</p>
                  </button>
                  <div className="rounded-[24px] border border-slate-200 p-4">
                    <h3 className="font-semibold">Submission context</h3>
                    <p className="mt-2 text-sm leading-6 text-slate-500">Submission: {submission?.id ?? 'Not ready'}</p>
                    <p className="text-sm leading-6 text-slate-500">Cycle: {currentCycle?.name ?? 'No cycle selected'}</p>
                    <p className="text-sm leading-6 text-slate-500">Evaluation: {evaluation?.status ?? 'Not generated yet'}</p>
                  </div>
                </div>
              </aside>
            </section>

            <section className="rounded-[28px] bg-white p-6 shadow-panel">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm uppercase tracking-[0.24em] text-ember">Status Flow</p>
                  <h2 className="mt-2 text-2xl font-bold">Evaluation lifecycle</h2>
                </div>
                <StatusIndicator status={currentStatus} />
              </div>
              <div className="mt-6 grid gap-3 md:grid-cols-4 xl:grid-cols-8">
                {FLOW.map((status, index) => {
                  const isDone = activeIndex >= index;
                  return (
                    <div key={status} className={`rounded-[22px] border px-4 py-4 text-center ${isDone ? 'border-ink bg-ink text-white' : 'border-slate-200 bg-slate-50 text-slate-500'}`}>
                      <div className="text-xs uppercase tracking-[0.18em]">Step {index + 1}</div>
                      <div className="mt-2 flex justify-center">
                        <StatusIndicator status={status} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>

            <section className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
              <div className="flex flex-col gap-6">
                <FileUploadPanel isUploading={isUploading} onFilesSelected={handleFilesSelected} />
                <FileList files={files} onDelete={handleDeleteFile} onRetryParse={handleRetryParse} />
              </div>
              <section className="rounded-[28px] bg-white p-6 shadow-panel">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm uppercase tracking-[0.24em] text-ember">Evidence</p>
                    <h2 className="mt-2 text-2xl font-bold">Extracted signals</h2>
                  </div>
                  <span className="text-sm text-slate-500">{evidenceItems.length} cards</span>
                </div>
                <div className="mt-5 grid gap-4">
                  {evidenceItems.map((item) => (
                    <EvidenceCard evidence={item} key={item.id} />
                  ))}
                </div>
              </section>
            </section>

            <section className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
              <div className="flex flex-col gap-6">
                <ReviewPanel
                  aiLevel={evaluation?.ai_level ?? 'Not generated'}
                  dimensions={dimensions}
                  isConfirming={isConfirming}
                  isSubmitting={isReviewSubmitting}
                  onConfirmEvaluation={handleConfirmEvaluation}
                  onReviewCommentChange={setReviewComment}
                  onReviewLevelChange={setReviewLevel}
                  onSubmitReview={handleSubmitReview}
                  reviewComment={reviewComment}
                  reviewLevel={reviewLevel}
                />
                <DimensionScoreEditor dimensions={dimensions} onChange={setDimensions} />
              </div>
              <div className="flex flex-col gap-6">
                <CalibrationCompareTable rows={calibrationRows} />
                <section className="rounded-[28px] bg-white p-6 shadow-panel">
                  <p className="text-sm uppercase tracking-[0.24em] text-ember">Salary Advice</p>
                  <h3 className="mt-2 text-2xl font-bold text-ink">Recommendation snapshot</h3>
                  {salaryRecommendation ? (
                    <dl className="mt-5 space-y-3 text-sm text-slate-600">
                      <div className="flex justify-between gap-4"><dt>Status</dt><dd>{salaryRecommendation.status}</dd></div>
                      <div className="flex justify-between gap-4"><dt>Current salary</dt><dd>{salaryRecommendation.current_salary}</dd></div>
                      <div className="flex justify-between gap-4"><dt>Recommended salary</dt><dd>{salaryRecommendation.recommended_salary}</dd></div>
                      <div className="flex justify-between gap-4"><dt>Final adjustment</dt><dd>{(salaryRecommendation.final_adjustment_ratio * 100).toFixed(2)}%</dd></div>
                    </dl>
                  ) : (
                    <p className="mt-4 text-sm text-slate-500">No salary recommendation has been generated for this evaluation yet.</p>
                  )}
                </section>
              </div>
            </section>
          </>
        ) : null}
      </div>
    </main>
  );
}
