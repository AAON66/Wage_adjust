import { useCallback, useEffect, useState } from 'react';

import { ExcelImportPanel } from '../components/eligibility-import/ExcelImportPanel';
import { AppShell } from '../components/layout/AppShell';
import { PerformanceRecordsFilters } from '../components/performance/PerformanceRecordsFilters';
import { PerformanceRecordsTable } from '../components/performance/PerformanceRecordsTable';
import { TierDistributionPanel } from '../components/performance/TierDistributionPanel';
import { fetchDepartmentNames } from '../services/eligibilityService';
import {
  getAvailableYears,
  getPerformanceRecords,
} from '../services/performanceService';
import type { ConfirmResponse, PerformanceRecordItem } from '../types/api';
import { showToast } from '../utils/toast';

const PAGE_SIZE = 50;

interface RecordsTableState {
  items: PerformanceRecordItem[];
  loading: boolean;
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

const INITIAL_TABLE: RecordsTableState = {
  items: [],
  loading: false,
  total: 0,
  page: 1,
  pageSize: PAGE_SIZE,
  totalPages: 1,
};

/**
 * Phase 34 D-13：HR 独立「绩效管理」页面（admin + hrbp 限定）。
 *
 * 3 section 垂直排列：
 *   1. 档次分布（TierDistributionPanel）— ECharts 堆叠条 + chip + 重算按钮 + 空状态
 *   2. 绩效记录导入（复用 Phase 32 ExcelImportPanel importType=performance_grades）
 *   3. 绩效记录列表（7 列 + filter + 分页）
 *
 * B-3：availableYears 用 getAvailableYears() 替代「拉 200 条 records 凑 distinct」hack
 * W-1：handleImportComplete 5 状态分支 toast 文案
 * W-4：所有 toast 走 showToast 单实例 helper
 */
export function PerformanceManagementPage() {
  const [selectedYear, setSelectedYear] = useState<number>(() => new Date().getFullYear());
  const [availableYears, setAvailableYears] = useState<number[]>([new Date().getFullYear()]);
  const [departments, setDepartments] = useState<string[]>([]);
  const [filterYear, setFilterYear] = useState<string>('');
  const [filterDepartment, setFilterDepartment] = useState<string>('');
  const [tableState, setTableState] = useState<RecordsTableState>(INITIAL_TABLE);
  const [tierRefreshKey, setTierRefreshKey] = useState<number>(0);

  // B-3：mount 时从后端 /available-years 拉年份；fallback 到当前年
  useEffect(() => {
    void getAvailableYears()
      .then((years) => {
        const fallback = years.length > 0 ? years : [new Date().getFullYear()];
        setAvailableYears(fallback);
        // 若后端返回的年份不含当前默认 selectedYear，切换到首个可用年
        if (!fallback.includes(selectedYear)) {
          setSelectedYear(fallback[0]);
        }
      })
      .catch(() => {
        setAvailableYears([new Date().getFullYear()]);
      });
    // 仅 mount 时执行一次；后续切换 selectedYear 不重新拉
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 拉部门列表
  useEffect(() => {
    void fetchDepartmentNames()
      .then(setDepartments)
      .catch(() => setDepartments([]));
  }, []);

  // 拉绩效记录（filter 或 page 变化时）
  const loadRecords = useCallback(
    async (overridePage?: number) => {
      const targetPage = overridePage ?? tableState.page;
      setTableState((prev) => ({ ...prev, loading: true }));
      try {
        const resp = await getPerformanceRecords({
          year: filterYear ? Number(filterYear) : null,
          department: filterDepartment || null,
          page: targetPage,
          page_size: PAGE_SIZE,
        });
        setTableState({
          items: resp.items,
          loading: false,
          total: resp.total,
          page: resp.page,
          pageSize: resp.page_size,
          totalPages: Math.max(1, resp.total_pages),
        });
      } catch (err) {
        setTableState((prev) => ({ ...prev, loading: false }));
        const msg = err instanceof Error ? err.message : '加载失败';
        showToast(`加载绩效记录失败：${msg}`, 'error');
      }
    },
    [filterYear, filterDepartment, tableState.page],
  );

  // mount + filter 变化时重拉（page=1）
  useEffect(() => {
    void loadRecords(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterYear, filterDepartment]);

  const handlePageChange = useCallback(
    (nextPage: number) => {
      setTableState((prev) => ({ ...prev, page: nextPage }));
      void loadRecords(nextPage);
    },
    [loadRecords],
  );

  // W-1：根据 ConfirmResponse.tier_recompute_status 5 分支 toast
  const handleImportComplete = useCallback(
    (result: ConfirmResponse) => {
      const inserted = result.inserted_count ?? 0;
      const updated = result.updated_count ?? 0;
      const total = inserted + updated;
      const status = result.tier_recompute_status;
      if (status === 'completed') {
        showToast(`导入完成（${total} 条），档次已刷新`, 'success');
      } else if (status === 'in_progress') {
        showToast(`导入完成（${total} 条），档次正在后台重算…`, 'info');
      } else if (status === 'busy_skipped') {
        showToast(`导入完成（${total} 条），系统繁忙后续自动重算`, 'warning');
      } else if (status === 'failed') {
        showToast(
          `导入完成（${total} 条）但档次重算失败，请手动点击「重算档次」`,
          'error',
        );
      } else {
        // null / 'skipped' / 非 performance_grades 路径
        showToast(`导入成功：${inserted} 条新增 / ${updated} 条更新`, 'success');
      }
      // 重拉 records + 触发 tier panel 重新拉 summary
      void loadRecords(1);
      setTierRefreshKey((k) => k + 1);
    },
    [loadRecords],
  );

  const handleRecomputed = useCallback(() => {
    setTierRefreshKey((k) => k + 1);
    void loadRecords(tableState.page);
  }, [loadRecords, tableState.page]);

  return (
    <AppShell
      title="绩效管理"
      description="HR 端：导入绩效记录、查看档次分布、手动触发档次重算"
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Section 1: 档次分布 */}
        <section className="surface" style={{ padding: 24 }}>
          <TierDistributionPanel
            key={tierRefreshKey}
            year={selectedYear}
            availableYears={availableYears}
            onYearChange={setSelectedYear}
            onRecomputed={handleRecomputed}
          />
        </section>

        {/* Section 2: 绩效记录导入（复用 Phase 32 ExcelImportPanel） */}
        <section className="surface" style={{ padding: 24 }}>
          <div className="section-head">
            <div>
              <h3 className="section-title">绩效记录导入</h3>
              <p className="section-note">复用 Phase 32 Excel 两阶段提交（Preview + Confirm）</p>
            </div>
          </div>
          <ExcelImportPanel
            importType="performance_grades"
            label="绩效等级"
            onComplete={handleImportComplete}
          />
        </section>

        {/* Section 3: 绩效记录列表 */}
        <section className="surface" style={{ padding: 24 }}>
          <div className="section-head">
            <div>
              <h3 className="section-title">绩效记录</h3>
              <p className="section-note">查看历史绩效记录，按年份和部门筛选</p>
            </div>
          </div>
          <PerformanceRecordsFilters
            year={filterYear}
            setYear={setFilterYear}
            department={filterDepartment}
            setDepartment={setFilterDepartment}
            availableYears={availableYears}
            departments={departments}
          />
          <PerformanceRecordsTable
            items={tableState.items}
            loading={tableState.loading}
            total={tableState.total}
            page={tableState.page}
            pageSize={tableState.pageSize}
            totalPages={tableState.totalPages}
            onPageChange={handlePageChange}
          />
        </section>
      </div>
    </AppShell>
  );
}
