import axios from 'axios';
import { Link, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';

import { CreateCycleForm } from '../components/cycle/CreateCycleForm';
import { createCycle, fetchCycles } from '../services/cycleService';
import type { CycleCreatePayload, CycleRecord } from '../types/api';

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (error.response?.data as { message?: string } | undefined)?.message ?? '评估周期操作失败。';
  }
  return '评估周期操作失败。';
}

export function CreateCyclePage() {
  const navigate = useNavigate();
  const [cycles, setCycles] = useState<CycleRecord[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadCycles() {
      try {
        const response = await fetchCycles();
        if (!cancelled) {
          setCycles(response.items);
        }
      } catch {
        if (!cancelled) {
          setCycles([]);
        }
      }
    }

    void loadCycles();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSubmit(payload: CycleCreatePayload) {
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      await createCycle(payload);
      navigate('/employees', { replace: true });
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-[linear-gradient(135deg,#fff7ed_0%,#ffffff_45%,#dbeafe_100%)] px-6 py-10 text-ink">
      <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[0.95fr_1.05fr]">
        <section className="rounded-[32px] bg-white p-8 shadow-panel">
          <p className="text-sm uppercase tracking-[0.3em] text-ember">Create Cycle</p>
          <h1 className="mt-3 text-3xl font-bold">创建评估周期</h1>
          <p className="mt-3 text-sm leading-7 text-slate-600">当前页面直接连接 `/api/v1/cycles`，创建成功后会跳转回员工列表页。</p>
          <div className="mt-6">
            <CreateCycleForm errorMessage={errorMessage} isSubmitting={isSubmitting} onSubmit={handleSubmit} />
          </div>
          <Link className="mt-6 inline-flex rounded-full border border-ink/15 px-5 py-3 text-sm font-semibold text-ink" to="/employees">
            返回员工列表
          </Link>
        </section>
        <section className="rounded-[32px] bg-slate-950/95 p-8 text-white shadow-panel">
          <h2 className="text-2xl font-semibold">已存在的评估周期</h2>
          <div className="mt-6 space-y-4">
            {cycles.map((cycle) => (
              <article key={cycle.id} className="rounded-[24px] border border-white/10 bg-white/5 p-5">
                <div className="flex items-center justify-between gap-4">
                  <h3 className="text-lg font-semibold">{cycle.name}</h3>
                  <span className="rounded-full bg-white/10 px-3 py-1 text-xs uppercase tracking-[0.2em] text-white/75">{cycle.status}</span>
                </div>
                <p className="mt-2 text-sm text-white/70">评估周期：{cycle.review_period}</p>
                <p className="mt-1 text-sm text-white/70">预算：{cycle.budget_amount}</p>
              </article>
            ))}
            {cycles.length === 0 ? <p className="text-sm text-white/60">当前还没有周期数据。</p> : null}
          </div>
        </section>
      </div>
    </main>
  );
}
