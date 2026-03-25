import axios from 'axios';
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { AppShell } from '../components/layout/AppShell';
import { BudgetSimulationPanel } from '../components/salary/BudgetSimulationPanel';
import { SalaryHistoryPanel } from '../components/salary/SalaryHistoryPanel';
import { useAuth } from '../hooks/useAuth';
import { fetchCycles } from '../services/cycleService';
import { fetchSalaryHistoryByEmployee, simulateSalary } from '../services/salaryService';
import type { CycleRecord, SalaryHistoryRecord, SalarySimulationResponse } from '../types/api';
import { canAccessDepartment, getScopedDepartmentNames, isDepartmentScopedRole } from '../utils/departmentScope';
import { formatAiLevel, formatCycleStatus } from '../utils/statusText';

type SalaryResultView = 'cards' | 'department' | 'history' | 'versions';
type SalarySortMode = 'adjustment_desc' | 'amount_desc' | 'salary_desc' | 'name_asc';

interface ScenarioItem {
  employee_id: string;
  employee_name: string;
  department: string;
  job_family: string;
  evaluation_id: string;
  ai_level: string;
  currentSalary: number;
  projectedSalary: number;
  increaseAmount: number;
  final_adjustment_ratio: number;
  scenarioAdjustmentRatio: number;
  scenarioRecommendedSalary: number;
  scenarioIncreaseAmount: number;
  hasManualOverride: boolean;
}

interface ScenarioDepartmentSummary {
  department: string;
  headcount: number;
  totalIncrease: number;
  averageAdjustment: number;
  projectedTotal: number;
}

interface SavedScenarioItem {
  employeeId: string;
  employeeName: string;
  department: string;
  jobFamily: string;
  aiLevel: string;
  currentSalary: number;
  baseAdjustmentRatio: number;
  scenarioAdjustmentRatio: number;
  baseRecommendedSalary: number;
  scenarioRecommendedSalary: number;
  scenarioIncreaseAmount: number;
  hasManualOverride: boolean;
}

interface SavedScenarioVersion {
  id: string;
  name: string;
  cycleId: string;
  cycleName: string;
  reviewPeriod: string;
  createdAt: string;
  budgetInput: string;
  effectiveBudget: number;
  recommendedCost: number;
  baseRecommendedCost: number;
  budgetUsageRate: number;
  averageAdjustmentRate: number;
  itemCount: number;
  departmentCount: number;
  manualOverrideCount: number;
  globalAdjustmentDelta: number;
  filters: {
    department: string;
    jobFamily: string;
  };
  manualAdjustmentMap: Record<string, number>;
  items: SavedScenarioItem[];
  departments: ScenarioDepartmentSummary[];
}

interface ComparisonEmployeeRow {
  employeeId: string;
  employeeName: string;
  department: string;
  leftAdjustment: number | null;
  rightAdjustment: number | null;
  deltaAdjustment: number;
  leftIncrease: number | null;
  rightIncrease: number | null;
  deltaIncrease: number;
  status: string;
}

interface ComparisonDepartmentRow {
  department: string;
  leftTotalIncrease: number;
  rightTotalIncrease: number;
  deltaIncrease: number;
  leftAverageAdjustment: number;
  rightAverageAdjustment: number;
  deltaAverageAdjustment: number;
  leftHeadcount: number;
  rightHeadcount: number;
}

const STORAGE_KEY = 'salary-simulator-scenarios-v1';
const CURRENT_SCENARIO_ID = '__current__';

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

function formatDeltaPercent(value: number): string {
  const sign = value > 0 ? '+' : value < 0 ? '-' : '';
  return `${sign}${Math.abs(value * 100).toFixed(2)}%`;
}

function saveBlob(blob: Blob, fileName: string): void {
  const url = window.URL.createObjectURL(blob);
  const link = window.document.createElement('a');
  link.href = url;
  link.download = fileName;
  window.document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (
      (error.response?.data as { detail?: string; message?: string } | undefined)?.detail ??
      (error.response?.data as { detail?: string; message?: string } | undefined)?.message ??
      '加载调薪沙盘失败。'
    );
  }
  return '加载调薪沙盘失败。';
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY', maximumFractionDigits: 0 }).format(value);
}

function formatDateTime(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatEditablePercent(value: number): string {
  return (value * 100).toFixed(2).replace(/\.00$/, '').replace(/(\.\d*[1-9])0+$/, '$1');
}

function createVersionName(cycleName: string, count: number): string {
  return `${cycleName} 方案 ${String(count).padStart(2, '0')}`;
}

function parseStoredVersions(): SavedScenarioVersion[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as SavedScenarioVersion[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function buildDepartmentSummary(items: Array<Pick<ScenarioItem, 'department' | 'scenarioIncreaseAmount' | 'scenarioAdjustmentRatio' | 'scenarioRecommendedSalary'>>): ScenarioDepartmentSummary[] {
  const grouped = new Map<string, ScenarioDepartmentSummary>();
  items.forEach((item) => {
    const current = grouped.get(item.department) ?? {
      department: item.department,
      headcount: 0,
      totalIncrease: 0,
      averageAdjustment: 0,
      projectedTotal: 0,
    };

    current.headcount += 1;
    current.totalIncrease += item.scenarioIncreaseAmount;
    current.averageAdjustment += item.scenarioAdjustmentRatio;
    current.projectedTotal += item.scenarioRecommendedSalary;
    grouped.set(item.department, current);
  });

  return Array.from(grouped.values())
    .map((item) => ({
      ...item,
      averageAdjustment: item.headcount ? item.averageAdjustment / item.headcount : 0,
    }))
    .sort((left, right) => right.totalIncrease - left.totalIncrease);
}

function resolveVersionById(versions: SavedScenarioVersion[], currentVersion: SavedScenarioVersion | null, id: string): SavedScenarioVersion | null {
  if (id === CURRENT_SCENARIO_ID) {
    return currentVersion;
  }
  return versions.find((item) => item.id === id) ?? null;
}

export function SalarySimulatorPage() {
  const { user } = useAuth();
  const [cycles, setCycles] = useState<CycleRecord[]>([]);
  const [selectedCycleId, setSelectedCycleId] = useState('');
  const [budgetInput, setBudgetInput] = useState('');
  const [departmentFilter, setDepartmentFilter] = useState('');
  const [jobFamilyFilter, setJobFamilyFilter] = useState('');
  const [resultView, setResultView] = useState<SalaryResultView>('cards');
  const [sortMode, setSortMode] = useState<SalarySortMode>('adjustment_desc');
  const [selectedEmployeeId, setSelectedEmployeeId] = useState('');
  const [globalAdjustmentDeltaInput, setGlobalAdjustmentDeltaInput] = useState('0');
  const [manualAdjustmentDraft, setManualAdjustmentDraft] = useState('');
  const [manualAdjustmentMap, setManualAdjustmentMap] = useState<Record<string, number>>({});
  const [simulation, setSimulation] = useState<SalarySimulationResponse | null>(null);
  const [salaryHistory, setSalaryHistory] = useState<SalaryHistoryRecord[]>([]);
  const [savedVersions, setSavedVersions] = useState<SavedScenarioVersion[]>([]);
  const [versionNameInput, setVersionNameInput] = useState('');
  const [compareLeftId, setCompareLeftId] = useState(CURRENT_SCENARIO_ID);
  const [compareRightId, setCompareRightId] = useState('');
  const [noticeMessage, setNoticeMessage] = useState<string | null>(null);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const isDepartmentScoped = isDepartmentScopedRole(user?.role);
  const scopedDepartments = useMemo(() => getScopedDepartmentNames(user), [user]);

  useEffect(() => {
    setSavedVersions(parseStoredVersions());
  }, []);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(savedVersions));
  }, [savedVersions]);

  useEffect(() => {
    let cancelled = false;

    async function loadCycles() {
      try {
        const response = await fetchCycles();
        if (cancelled) {
          return;
        }
        setCycles(response.items);
        const firstCycle = response.items[0];
        if (firstCycle) {
          setSelectedCycleId(firstCycle.id);
          setBudgetInput('');
        }
      } catch (error) {
        if (!cancelled) {
          setErrorMessage(resolveError(error));
        }
      }
    }

    void loadCycles();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!isDepartmentScoped || canAccessDepartment(user, departmentFilter)) {
      return;
    }
    setDepartmentFilter('');
  }, [departmentFilter, isDepartmentScoped, user]);

  useEffect(() => {
    let cancelled = false;

    async function loadSimulation() {
      if (!selectedCycleId) {
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      setErrorMessage(null);

      try {
        const response = await simulateSalary({
          cycle_id: selectedCycleId,
          budget_amount: budgetInput.trim() ? budgetInput.trim() : undefined,
          department: departmentFilter || undefined,
          job_family: jobFamilyFilter || undefined,
        });

        if (!cancelled) {
          setSimulation(response);
        }
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

    void loadSimulation();
    return () => {
      cancelled = true;
    };
  }, [selectedCycleId, budgetInput, departmentFilter, jobFamilyFilter]);

  const selectedCycle = useMemo(() => cycles.find((cycle) => cycle.id === selectedCycleId) ?? null, [cycles, selectedCycleId]);

  const globalAdjustmentDelta = useMemo(() => {
    const parsed = Number(globalAdjustmentDeltaInput);
    return Number.isFinite(parsed) ? parsed / 100 : 0;
  }, [globalAdjustmentDeltaInput]);

  const baseItems = useMemo(
    () =>
      (simulation?.items ?? []).map((item) => {
        const currentSalary = Number(item.current_salary);
        const projectedSalary = Number(item.recommended_salary);
        return {
          ...item,
          currentSalary,
          projectedSalary,
          increaseAmount: projectedSalary - currentSalary,
        };
      }),
    [simulation?.items],
  );

  const scenarioItems = useMemo<ScenarioItem[]>(
    () =>
      baseItems.map((item) => {
        const manualRatio = manualAdjustmentMap[item.employee_id];
        const scenarioAdjustmentRatio = manualRatio ?? Math.max(item.final_adjustment_ratio + globalAdjustmentDelta, 0);
        const scenarioRecommendedSalary = item.currentSalary * (1 + scenarioAdjustmentRatio);
        return {
          ...item,
          scenarioAdjustmentRatio,
          scenarioRecommendedSalary,
          scenarioIncreaseAmount: scenarioRecommendedSalary - item.currentSalary,
          hasManualOverride: manualRatio != null,
        };
      }),
    [baseItems, globalAdjustmentDelta, manualAdjustmentMap],
  );

  const employees = useMemo(
    () =>
      scenarioItems.map((item) => ({
        id: item.employee_id,
        name: item.employee_name,
        department: item.department,
        currentSalary: item.currentSalary,
        suggestedIncreaseRate: item.scenarioAdjustmentRatio,
      })),
    [scenarioItems],
  );

  const baseRecommendedCost = useMemo(() => Number(simulation?.total_recommended_amount ?? 0), [simulation]);
  const recommendedCost = useMemo(() => scenarioItems.reduce((sum, item) => sum + item.scenarioIncreaseAmount, 0), [scenarioItems]);
  const effectiveBudget = useMemo(
    () => Number(simulation?.budget_amount ?? selectedCycle?.budget_amount ?? 0),
    [selectedCycle?.budget_amount, simulation?.budget_amount],
  );
  const budgetUsageRate = useMemo(() => (effectiveBudget > 0 ? recommendedCost / effectiveBudget : 0), [effectiveBudget, recommendedCost]);

  const selectedEmployee = useMemo(
    () => scenarioItems.find((item) => item.employee_id === selectedEmployeeId) ?? null,
    [scenarioItems, selectedEmployeeId],
  );

  const rankedItems = useMemo(() => {
    const items = [...scenarioItems];

    return items.sort((left, right) => {
      if (sortMode === 'adjustment_desc') {
        return right.scenarioAdjustmentRatio - left.scenarioAdjustmentRatio;
      }
      if (sortMode === 'amount_desc') {
        return right.scenarioIncreaseAmount - left.scenarioIncreaseAmount;
      }
      if (sortMode === 'salary_desc') {
        return right.scenarioRecommendedSalary - left.scenarioRecommendedSalary;
      }
      return left.employee_name.localeCompare(right.employee_name, 'zh-CN');
    });
  }, [scenarioItems, sortMode]);

  const departmentSummary = useMemo(() => buildDepartmentSummary(scenarioItems), [scenarioItems]);

  const averageAdjustmentRate = useMemo(
    () => (scenarioItems.length ? scenarioItems.reduce((sum, item) => sum + item.scenarioAdjustmentRatio, 0) / scenarioItems.length : 0),
    [scenarioItems],
  );

  const maxAdjustmentItem = useMemo(
    () =>
      scenarioItems.reduce<ScenarioItem | null>(
        (current, item) => (current == null || item.scenarioAdjustmentRatio > current.scenarioAdjustmentRatio ? item : current),
        null,
      ),
    [scenarioItems],
  );

  const departmentBudgetComparison = useMemo(() => {
    const budgetMap = new Map((selectedCycle?.department_budgets ?? []).map((item) => [item.department_name, Number(item.budget_amount)]));
    const allDepartments = Array.from(new Set([...departmentSummary.map((item) => item.department), ...budgetMap.keys()]));
    return allDepartments
      .map((department) => {
        const summary = departmentSummary.find((item) => item.department === department);
        const configuredBudget = budgetMap.get(department) ?? null;
        const usedBudget = summary?.totalIncrease ?? 0;
        const remainingBudget = configuredBudget == null ? null : configuredBudget - usedBudget;
        return {
          department,
          configuredBudget,
          usedBudget,
          remainingBudget,
          headcount: summary?.headcount ?? 0,
          averageAdjustment: summary?.averageAdjustment ?? 0,
        };
      })
      .sort((left, right) => right.usedBudget - left.usedBudget);
  }, [departmentSummary, selectedCycle?.department_budgets]);

  const currentScenarioVersion = useMemo<SavedScenarioVersion | null>(() => {
    if (!selectedCycleId || !scenarioItems.length) {
      return null;
    }

    return {
      id: CURRENT_SCENARIO_ID,
      name: '当前试算',
      cycleId: selectedCycleId,
      cycleName: selectedCycle?.name ?? '当前周期',
      reviewPeriod: selectedCycle?.review_period ?? '',
      createdAt: new Date().toISOString(),
      budgetInput,
      effectiveBudget,
      recommendedCost,
      baseRecommendedCost,
      budgetUsageRate,
      averageAdjustmentRate,
      itemCount: scenarioItems.length,
      departmentCount: departmentSummary.length,
      manualOverrideCount: scenarioItems.filter((item) => item.hasManualOverride).length,
      globalAdjustmentDelta,
      filters: {
        department: departmentFilter,
        jobFamily: jobFamilyFilter,
      },
      manualAdjustmentMap: { ...manualAdjustmentMap },
      items: scenarioItems.map((item) => ({
        employeeId: item.employee_id,
        employeeName: item.employee_name,
        department: item.department,
        jobFamily: item.job_family,
        aiLevel: item.ai_level,
        currentSalary: item.currentSalary,
        baseAdjustmentRatio: item.final_adjustment_ratio,
        scenarioAdjustmentRatio: item.scenarioAdjustmentRatio,
        baseRecommendedSalary: item.projectedSalary,
        scenarioRecommendedSalary: item.scenarioRecommendedSalary,
        scenarioIncreaseAmount: item.scenarioIncreaseAmount,
        hasManualOverride: item.hasManualOverride,
      })),
      departments: departmentSummary,
    };
  }, [
    averageAdjustmentRate,
    baseRecommendedCost,
    budgetInput,
    budgetUsageRate,
    departmentFilter,
    departmentSummary,
    effectiveBudget,
    globalAdjustmentDelta,
    jobFamilyFilter,
    manualAdjustmentMap,
    recommendedCost,
    scenarioItems,
    selectedCycle?.name,
    selectedCycle?.review_period,
    selectedCycleId,
  ]);

  const cycleVersions = useMemo(
    () => savedVersions.filter((item) => !selectedCycleId || item.cycleId === selectedCycleId),
    [savedVersions, selectedCycleId],
  );

  const compareOptions = useMemo(() => {
    const options = [];
    if (currentScenarioVersion) {
      options.push({ id: CURRENT_SCENARIO_ID, label: `当前试算 · ${currentScenarioVersion.cycleName}` });
    }
    options.push(
      ...cycleVersions.map((item) => ({
        id: item.id,
        label: `${item.name} · ${formatDateTime(item.createdAt)}`,
      })),
    );
    return options;
  }, [currentScenarioVersion, cycleVersions]);

  const leftVersion = useMemo(
    () => resolveVersionById(cycleVersions, currentScenarioVersion, compareLeftId),
    [compareLeftId, currentScenarioVersion, cycleVersions],
  );

  const rightVersion = useMemo(
    () => resolveVersionById(cycleVersions, currentScenarioVersion, compareRightId),
    [compareRightId, currentScenarioVersion, cycleVersions],
  );

  const versionComparison = useMemo(() => {
    if (!leftVersion || !rightVersion) {
      return null;
    }

    const leftItems = new Map(leftVersion.items.map((item) => [item.employeeId, item]));
    const rightItems = new Map(rightVersion.items.map((item) => [item.employeeId, item]));
    const employeeIds = Array.from(new Set([...leftItems.keys(), ...rightItems.keys()]));

    const employeeRows = employeeIds
      .map<ComparisonEmployeeRow | null>((employeeId) => {
        const leftItem = leftItems.get(employeeId) ?? null;
        const rightItem = rightItems.get(employeeId) ?? null;
        const leftAdjustment = leftItem?.scenarioAdjustmentRatio ?? null;
        const rightAdjustment = rightItem?.scenarioAdjustmentRatio ?? null;
        const leftIncrease = leftItem?.scenarioIncreaseAmount ?? null;
        const rightIncrease = rightItem?.scenarioIncreaseAmount ?? null;
        const deltaAdjustment = (rightAdjustment ?? 0) - (leftAdjustment ?? 0);
        const deltaIncrease = (rightIncrease ?? 0) - (leftIncrease ?? 0);
        const hasValueDifference = Math.abs(deltaAdjustment) > 0.00001 || Math.abs(deltaIncrease) > 0.01;
        const hasManualDifference = (leftItem?.hasManualOverride ?? false) !== (rightItem?.hasManualOverride ?? false);

        if (!leftItem && !rightItem) {
          return null;
        }

        if (!leftItem || !rightItem || hasValueDifference || hasManualDifference) {
          return {
            employeeId,
            employeeName: rightItem?.employeeName ?? leftItem?.employeeName ?? employeeId,
            department: rightItem?.department ?? leftItem?.department ?? '-',
            leftAdjustment,
            rightAdjustment,
            deltaAdjustment,
            leftIncrease,
            rightIncrease,
            deltaIncrease,
            status: !leftItem ? '仅右侧方案' : !rightItem ? '仅左侧方案' : hasManualDifference ? '人工覆盖变化' : '调幅变化',
          };
        }

        return null;
      })
      .filter((item): item is ComparisonEmployeeRow => item != null)
      .sort((left, right) => Math.abs(right.deltaIncrease) - Math.abs(left.deltaIncrease));

    const leftDepartments = new Map(leftVersion.departments.map((item) => [item.department, item]));
    const rightDepartments = new Map(rightVersion.departments.map((item) => [item.department, item]));
    const allDepartments = Array.from(new Set([...leftDepartments.keys(), ...rightDepartments.keys()]));

    const departmentRows = allDepartments
      .map<ComparisonDepartmentRow>((department) => {
        const leftItem = leftDepartments.get(department);
        const rightItem = rightDepartments.get(department);
        const leftTotalIncrease = leftItem?.totalIncrease ?? 0;
        const rightTotalIncrease = rightItem?.totalIncrease ?? 0;
        return {
          department,
          leftTotalIncrease,
          rightTotalIncrease,
          deltaIncrease: rightTotalIncrease - leftTotalIncrease,
          leftAverageAdjustment: leftItem?.averageAdjustment ?? 0,
          rightAverageAdjustment: rightItem?.averageAdjustment ?? 0,
          deltaAverageAdjustment: (rightItem?.averageAdjustment ?? 0) - (leftItem?.averageAdjustment ?? 0),
          leftHeadcount: leftItem?.headcount ?? 0,
          rightHeadcount: rightItem?.headcount ?? 0,
        };
      })
      .sort((left, right) => Math.abs(right.deltaIncrease) - Math.abs(left.deltaIncrease));

    return {
      totalCostDelta: rightVersion.recommendedCost - leftVersion.recommendedCost,
      averageAdjustmentDelta: rightVersion.averageAdjustmentRate - leftVersion.averageAdjustmentRate,
      budgetUsageDelta: rightVersion.budgetUsageRate - leftVersion.budgetUsageRate,
      manualOverrideDelta: rightVersion.manualOverrideCount - leftVersion.manualOverrideCount,
      changedEmployees: employeeRows,
      departmentRows,
    };
  }, [leftVersion, rightVersion]);

  useEffect(() => {
    const firstEmployeeId = scenarioItems[0]?.employee_id ?? '';
    if (!firstEmployeeId) {
      setSelectedEmployeeId('');
      setSalaryHistory([]);
      return;
    }
    setSelectedEmployeeId((current) => (current && scenarioItems.some((item) => item.employee_id === current) ? current : firstEmployeeId));
  }, [scenarioItems]);

  useEffect(() => {
    if (!selectedEmployee) {
      setManualAdjustmentDraft('');
      return;
    }
    setManualAdjustmentDraft((selectedEmployee.scenarioAdjustmentRatio * 100).toFixed(2));
  }, [selectedEmployee]);

  useEffect(() => {
    const availableIds = cycleVersions.map((item) => item.id);
    setCompareLeftId((current) => (current === CURRENT_SCENARIO_ID || availableIds.includes(current) ? current : CURRENT_SCENARIO_ID));
  }, [cycleVersions]);

  useEffect(() => {
    const availableIds = cycleVersions.map((item) => item.id);
    setCompareRightId((current) => {
      if (current && current !== compareLeftId && availableIds.includes(current)) {
        return current;
      }
      return availableIds.find((item) => item !== compareLeftId) ?? availableIds[0] ?? '';
    });
  }, [compareLeftId, cycleVersions]);

  useEffect(() => {
    let cancelled = false;

    async function loadSalaryHistory() {
      if (!selectedEmployeeId) {
        setSalaryHistory([]);
        return;
      }

      setIsHistoryLoading(true);

      try {
        const response = await fetchSalaryHistoryByEmployee(selectedEmployeeId);
        if (!cancelled) {
          setSalaryHistory(response.items);
        }
      } catch (error) {
        if (!cancelled) {
          setSalaryHistory([]);
          setErrorMessage(resolveError(error));
        }
      } finally {
        if (!cancelled) {
          setIsHistoryLoading(false);
        }
      }
    }

    void loadSalaryHistory();
    return () => {
      cancelled = true;
    };
  }, [selectedEmployeeId]);

  function handleApplyManualAdjustment() {
    if (!selectedEmployeeId) {
      return;
    }

    const parsed = Number(manualAdjustmentDraft);
    if (!Number.isFinite(parsed) || parsed < 0) {
      setErrorMessage('请输入有效的手动调幅，且不能小于 0。');
      return;
    }

    setErrorMessage(null);
    setNoticeMessage(null);
    setManualAdjustmentMap((current) => ({ ...current, [selectedEmployeeId]: parsed / 100 }));
  }

  function handleResetEmployeeAdjustment() {
    if (!selectedEmployeeId) {
      return;
    }

    setManualAdjustmentMap((current) => {
      const next = { ...current };
      delete next[selectedEmployeeId];
      return next;
    });
    setNoticeMessage(null);
  }

  function handleResetScenario() {
    setGlobalAdjustmentDeltaInput('0');
    setManualAdjustmentMap({});
    setErrorMessage(null);
    setNoticeMessage('已恢复为系统基线方案。');
  }

  function handleExportScenario() {
    const lines = [
      ['员工姓名', '工号', '部门', '岗位族', 'AI 等级', '当前薪资', '基线调幅', '试算调幅', '基线调后薪资', '试算调后薪资', '试算涨薪金额', '是否手动覆盖'].join(','),
      ...rankedItems.map((item) =>
        [
          item.employee_name,
          item.employee_id,
          item.department,
          item.job_family,
          formatAiLevel(item.ai_level),
          item.currentSalary.toFixed(2),
          `${(item.final_adjustment_ratio * 100).toFixed(2)}%`,
          `${(item.scenarioAdjustmentRatio * 100).toFixed(2)}%`,
          item.projectedSalary.toFixed(2),
          item.scenarioRecommendedSalary.toFixed(2),
          item.scenarioIncreaseAmount.toFixed(2),
          item.hasManualOverride ? '是' : '否',
        ]
          .map((value) => `"${String(value).replace(/"/g, '""')}"`)
          .join(','),
      ),
    ];

    const blob = new Blob(['\uFEFF' + lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    saveBlob(blob, `salary-sandbox-${selectedCycleId || 'current'}.csv`);
    setNoticeMessage('已导出当前沙盘结果。');
  }

  function handleSaveVersion() {
    if (!currentScenarioVersion) {
      setErrorMessage('当前没有可保存的试算结果。');
      return;
    }

    const nextVersion: SavedScenarioVersion = {
      ...currentScenarioVersion,
      id: `${currentScenarioVersion.cycleId}-${Date.now()}`,
      name: versionNameInput.trim() || createVersionName(currentScenarioVersion.cycleName, cycleVersions.length + 1),
      createdAt: new Date().toISOString(),
      manualAdjustmentMap: { ...currentScenarioVersion.manualAdjustmentMap },
      items: currentScenarioVersion.items.map((item) => ({ ...item })),
      departments: currentScenarioVersion.departments.map((item) => ({ ...item })),
    };

    setSavedVersions((current) => [nextVersion, ...current]);
    setVersionNameInput('');
    setResultView('versions');
    setCompareLeftId(CURRENT_SCENARIO_ID);
    setCompareRightId(nextVersion.id);
    setErrorMessage(null);
    setNoticeMessage(`已保存方案版本：${nextVersion.name}`);
  }

  function handleApplyVersion(version: SavedScenarioVersion) {
    setSelectedCycleId(version.cycleId);
    setBudgetInput(version.budgetInput);
    setDepartmentFilter(version.filters.department);
    setJobFamilyFilter(version.filters.jobFamily);
    setGlobalAdjustmentDeltaInput(formatEditablePercent(version.globalAdjustmentDelta));
    setManualAdjustmentMap({ ...version.manualAdjustmentMap });
    setSelectedEmployeeId(version.items[0]?.employeeId ?? '');
    setResultView('cards');
    setErrorMessage(null);
    setNoticeMessage(`已载入方案：${version.name}`);
  }

  function handleDeleteVersion(versionId: string) {
    const deletingVersion = savedVersions.find((item) => item.id === versionId);
    setSavedVersions((current) => current.filter((item) => item.id !== versionId));
    setNoticeMessage(deletingVersion ? `已删除方案：${deletingVersion.name}` : '已删除方案。');
  }

  return (
    <AppShell
      title="调薪建议沙盘"
      description="按预算、筛选条件和方案版本推演当前周期的调薪结果。"
      actions={
        <>
          <Link className="action-secondary" to="/workspace">
            返回工作区
          </Link>
          <Link className="action-primary" to="/approvals">
            打开审批中心
          </Link>
        </>
      }
    >
      <section className="surface animate-fade-up px-6 py-6 lg:px-7">
        <div className="grid gap-3 md:grid-cols-2">
          <label className="surface-subtle px-4 py-4">
            <span className="text-sm text-steel">当前周期</span>
            <select
              className="toolbar-input mt-3 w-full"
              onChange={(event) => {
                setSelectedCycleId(event.target.value);
                setBudgetInput('');
                setNoticeMessage(null);
              }}
              value={selectedCycleId}
            >
              {cycles.map((cycle) => (
                <option key={cycle.id} value={cycle.id}>
                  {cycle.name}
                </option>
              ))}
            </select>
          </label>
          <div className="surface-subtle px-4 py-4">
            <span className="text-sm text-steel">周期信息</span>
            <p className="mt-3 text-lg font-semibold text-ink">{selectedCycle?.review_period ?? '未选择周期'}</p>
            <p className="mt-2 text-sm text-steel">状态：{formatCycleStatus(selectedCycle?.status)}</p>
          </div>
        </div>
      </section>

      <BudgetSimulationPanel
        budgetInput={budgetInput}
        departmentFilter={departmentFilter}
        effectiveBudget={effectiveBudget}
        employees={employees}
        isDepartmentScoped={isDepartmentScoped}
        jobFamilyFilter={jobFamilyFilter}
        onBudgetAmountChange={setBudgetInput}
        onDepartmentFilterChange={setDepartmentFilter}
        onJobFamilyFilterChange={setJobFamilyFilter}
        recommendedCost={recommendedCost}
        scopedDepartments={scopedDepartments}
      />

      {isLoading ? <p className="px-2 text-sm text-steel">正在加载调薪沙盘...</p> : null}
      {errorMessage ? (
        <p className="surface px-5 py-4 text-sm" style={{ color: 'var(--color-danger)' }}>
          {errorMessage}
        </p>
      ) : null}
      {noticeMessage ? (
        <p className="surface px-5 py-4 text-sm" style={{ color: 'var(--color-success)' }}>
          {noticeMessage}
        </p>
      ) : null}

      <section className="metric-strip animate-fade-up">
        {[
          ['预算使用率', `${Math.min(Math.max(budgetUsageRate * 100, 0), 999).toFixed(1)}%`, simulation?.over_budget ? '当前试算已超出预算。' : '当前试算仍在预算范围内。'],
          ['平均调幅', `${(averageAdjustmentRate * 100).toFixed(2)}%`, '基于当前筛选结果和试算参数计算。'],
          ['最高调幅', maxAdjustmentItem ? `${(maxAdjustmentItem.scenarioAdjustmentRatio * 100).toFixed(2)}%` : '--', maxAdjustmentItem ? `${maxAdjustmentItem.employee_name} / ${maxAdjustmentItem.department}` : '暂无结果'],
          ['覆盖部门', `${departmentSummary.length}`, '当前沙盘结果覆盖的部门数量。'],
        ].map(([label, value, note]) => (
          <article className="metric-tile" key={label}>
            <p className="metric-label">{label}</p>
            <p className="metric-value text-[26px]">{value}</p>
            <p className="metric-note">{note}</p>
          </article>
        ))}
      </section>

      <section className="surface animate-fade-up px-6 py-6 lg:px-7">
        <div className="section-head">
          <div>
            <p className="eyebrow">试算工具</p>
            <h2 className="section-title">手动调幅试算</h2>
            <p className="section-note">支持全员统一偏移，也支持对单个员工做手动覆盖。</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button className="action-secondary" onClick={handleResetScenario} type="button">
              恢复基线方案
            </button>
            <button className="action-primary" onClick={handleExportScenario} type="button">
              导出当前结果
            </button>
          </div>
        </div>

        <div className="mt-5 grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
          <div className="surface-subtle px-4 py-4">
            <p className="text-sm font-medium text-ink">全员统一偏移</p>
            <p className="mt-1 text-sm text-steel">在系统建议调幅上统一加减百分点，快速放宽或收紧方案。</p>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <input
                className="toolbar-input w-[180px]"
                onChange={(event) => setGlobalAdjustmentDeltaInput(event.target.value)}
                placeholder="例如 1.5"
                type="number"
                value={globalAdjustmentDeltaInput}
              />
              <span className="text-sm text-steel">个百分点</span>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <div className="surface px-4 py-3">
                <p className="text-xs uppercase tracking-[0.14em] text-placeholder">基线总额</p>
                <p className="mt-2 text-sm font-semibold text-ink">{formatCurrency(baseRecommendedCost)}</p>
              </div>
              <div className="surface px-4 py-3">
                <p className="text-xs uppercase tracking-[0.14em] text-placeholder">试算总额</p>
                <p className="mt-2 text-sm font-semibold text-ink">{formatCurrency(recommendedCost)}</p>
              </div>
              <div className="surface px-4 py-3">
                <p className="text-xs uppercase tracking-[0.14em] text-placeholder">差额</p>
                <p
                  className="mt-2 text-sm font-semibold"
                  style={{ color: recommendedCost - baseRecommendedCost >= 0 ? 'var(--color-danger)' : 'var(--color-success)' }}
                >
                  {formatCurrency(recommendedCost - baseRecommendedCost)}
                </p>
              </div>
            </div>
          </div>

          <div className="surface-subtle px-4 py-4">
            <p className="text-sm font-medium text-ink">单人手动覆盖</p>
            <p className="mt-1 text-sm text-steel">对重点员工单独试算，不受全员偏移限制。</p>
            <div className="mt-4 grid gap-3 md:grid-cols-[minmax(0,1fr)_160px_auto_auto]">
              <select className="toolbar-input" onChange={(event) => setSelectedEmployeeId(event.target.value)} value={selectedEmployeeId}>
                <option value="">请选择员工</option>
                {rankedItems.map((item) => (
                  <option key={item.employee_id} value={item.employee_id}>
                    {item.employee_name} / {item.department}
                  </option>
                ))}
              </select>
              <input
                className="toolbar-input"
                onChange={(event) => setManualAdjustmentDraft(event.target.value)}
                placeholder="调幅 %"
                type="number"
                value={manualAdjustmentDraft}
              />
              <button className="action-primary" onClick={handleApplyManualAdjustment} type="button">
                应用
              </button>
              <button className="action-secondary" onClick={handleResetEmployeeAdjustment} type="button">
                重置
              </button>
            </div>
            {selectedEmployee ? (
              <div className="mt-4 grid gap-3 md:grid-cols-3">
                <div className="surface px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.14em] text-placeholder">基线调幅</p>
                  <p className="mt-2 text-sm font-semibold text-ink">{formatPercent(selectedEmployee.final_adjustment_ratio)}</p>
                </div>
                <div className="surface px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.14em] text-placeholder">试算调幅</p>
                  <p className="mt-2 text-sm font-semibold text-ink">{formatPercent(selectedEmployee.scenarioAdjustmentRatio)}</p>
                </div>
                <div className="surface px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.14em] text-placeholder">试算涨薪金额</p>
                  <p className="mt-2 text-sm font-semibold text-ink">{formatCurrency(selectedEmployee.scenarioIncreaseAmount)}</p>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </section>

      <section className="surface" style={{ padding: '16px 20px' }}>
        <div className="section-head">
          <div>
            <p className="eyebrow">模拟结果</p>
            <h2 className="section-title">调薪沙盘工作区</h2>
          </div>
          <div className="flex flex-wrap gap-2">
            {([
              ['cards', '建议名单'],
              ['department', '部门汇总'],
              ['history', '历史走势'],
              ['versions', '方案版本'],
            ] as const).map(([value, label]) => (
              <button
                className={resultView === value ? 'chip-button chip-button-active' : 'chip-button'}
                key={value}
                onClick={() => setResultView(value)}
                type="button"
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {resultView !== 'versions' ? (
          <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
            <span className="text-sm text-steel">{rankedItems.length} 名员工</span>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm text-steel">排序方式</span>
              <select className="toolbar-input min-w-[180px]" onChange={(event) => setSortMode(event.target.value as SalarySortMode)} value={sortMode}>
                <option value="adjustment_desc">按调幅从高到低</option>
                <option value="amount_desc">按涨薪金额从高到低</option>
                <option value="salary_desc">按调后薪资从高到低</option>
                <option value="name_asc">按姓名排序</option>
              </select>
            </div>
          </div>
        ) : null}

        {!rankedItems.length && resultView !== 'versions' ? (
          <div className="mt-5 surface-subtle px-5 py-5 text-sm text-steel">当前条件下没有可展示的模拟结果。</div>
        ) : null}
        {resultView === 'cards' && rankedItems.length ? (
          <div className="mt-5 grid gap-4 md:grid-cols-2">
            {rankedItems.map((item) => (
              <article
                className="list-row"
                key={item.employee_id}
                style={selectedEmployeeId === item.employee_id ? { borderColor: 'var(--color-primary-border)', background: 'var(--color-primary-light)' } : undefined}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 style={{ fontSize: 15, fontWeight: 600, color: 'var(--color-ink)' }}>{item.employee_name}</h3>
                    <p className="mt-1 text-sm text-steel">
                      {item.department} / {item.job_family}
                    </p>
                  </div>
                  <span className="status-pill" style={{ background: 'var(--color-info-bg)', color: 'var(--color-info)' }}>
                    {(item.scenarioAdjustmentRatio * 100).toFixed(1)}%
                  </span>
                </div>
                <dl className="mt-5 space-y-3 text-sm text-steel">
                  <div className="flex justify-between gap-4">
                    <dt>AI 等级</dt>
                    <dd className="text-ink">{formatAiLevel(item.ai_level)}</dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt>当前薪资</dt>
                    <dd className="text-ink">{formatCurrency(item.currentSalary)}</dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt>建议涨薪金额</dt>
                    <dd className="text-ink">{formatCurrency(item.scenarioIncreaseAmount)}</dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt>调整后薪资</dt>
                    <dd className="text-ink">{formatCurrency(item.scenarioRecommendedSalary)}</dd>
                  </div>
                </dl>
                <div className="mt-4 flex flex-wrap gap-2 text-xs text-steel">
                  <span className="status-pill" style={{ background: 'var(--color-bg-subtle)', color: 'var(--color-steel)' }}>
                    基线 {formatPercent(item.final_adjustment_ratio)}
                  </span>
                  {item.hasManualOverride ? (
                    <span className="status-pill" style={{ background: 'var(--color-primary-light)', color: 'var(--color-primary)' }}>
                      已手动覆盖
                    </span>
                  ) : null}
                </div>
                <div className="mt-5 flex flex-wrap gap-3">
                  <button className="action-secondary" onClick={() => setSelectedEmployeeId(item.employee_id)} type="button">
                    选中员工
                  </button>
                  <button
                    className="action-primary"
                    onClick={() => {
                      setSelectedEmployeeId(item.employee_id);
                      setResultView('history');
                    }}
                    type="button"
                  >
                    查看历史走势
                  </button>
                </div>
              </article>
            ))}
          </div>
        ) : null}

        {resultView === 'department' && departmentSummary.length ? (
          <div className="mt-5 grid gap-5">
            <div className="grid gap-4 lg:grid-cols-2">
              {departmentSummary.map((item) => (
                <article className="surface-subtle px-5 py-5" key={item.department}>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="text-base font-semibold text-ink">{item.department}</h3>
                      <p className="mt-1 text-sm text-steel">{item.headcount} 人参与当前试算</p>
                    </div>
                    <span className="status-pill" style={{ background: 'var(--color-primary-light)', color: 'var(--color-primary)' }}>
                      {(item.averageAdjustment * 100).toFixed(2)}%
                    </span>
                  </div>
                  <dl className="mt-5 space-y-3 text-sm text-steel">
                    <div className="flex justify-between gap-4">
                      <dt>预计增加总额</dt>
                      <dd className="text-ink">{formatCurrency(item.totalIncrease)}</dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt>平均调幅</dt>
                      <dd className="text-ink">{(item.averageAdjustment * 100).toFixed(2)}%</dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt>调后薪资总额</dt>
                      <dd className="text-ink">{formatCurrency(item.projectedTotal)}</dd>
                    </div>
                  </dl>
                </article>
              ))}
            </div>

            <section className="surface-subtle px-5 py-5">
              <div className="section-head">
                <div>
                  <p className="eyebrow">预算对比</p>
                  <h3 className="section-title">部门预算对比表</h3>
                </div>
                <p className="section-note">对照周期配置的部门预算，查看当前试算方案的占用情况。</p>
              </div>
              <div className="table-shell mt-4">
                <div className="overflow-x-auto">
                  <table className="table-lite">
                    <thead>
                      <tr>
                        <th>部门</th>
                        <th>试算人数</th>
                        <th>配置预算</th>
                        <th>试算占用</th>
                        <th>剩余预算</th>
                        <th>平均调幅</th>
                      </tr>
                    </thead>
                    <tbody>
                      {departmentBudgetComparison.map((item) => (
                        <tr key={item.department}>
                          <td>{item.department}</td>
                          <td>{item.headcount}</td>
                          <td>{item.configuredBudget == null ? '未配置' : formatCurrency(item.configuredBudget)}</td>
                          <td>{formatCurrency(item.usedBudget)}</td>
                          <td
                            style={{
                              color:
                                item.remainingBudget == null
                                  ? 'var(--color-steel)'
                                  : item.remainingBudget >= 0
                                    ? 'var(--color-success)'
                                    : 'var(--color-danger)',
                              fontWeight: 600,
                            }}
                          >
                            {item.remainingBudget == null ? '未配置' : formatCurrency(item.remainingBudget)}
                          </td>
                          <td>{formatPercent(item.averageAdjustment)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </section>
          </div>
        ) : null}

        {resultView === 'history' ? (
          <div className="mt-5 grid gap-5 xl:grid-cols-[320px_minmax(0,1fr)]">
            <aside className="surface-subtle px-4 py-4">
              <p className="text-sm font-semibold text-ink">选择员工</p>
              <div className="mt-4 grid gap-2">
                {rankedItems.map((item) => (
                  <button
                    key={item.employee_id}
                    onClick={() => setSelectedEmployeeId(item.employee_id)}
                    style={{
                      textAlign: 'left',
                      borderRadius: 8,
                      border: `1px solid ${selectedEmployeeId === item.employee_id ? 'var(--color-primary-border)' : 'var(--color-border)'}`,
                      background: selectedEmployeeId === item.employee_id ? 'var(--color-primary-light)' : '#FFFFFF',
                      padding: '12px 14px',
                    }}
                    type="button"
                  >
                    <p className="text-sm font-semibold text-ink">{item.employee_name}</p>
                    <p className="mt-1 text-xs text-steel">
                      {item.department} / {item.job_family}
                    </p>
                    <p className="mt-2 text-xs text-steel">当前试算 {formatPercent(item.scenarioAdjustmentRatio)}</p>
                  </button>
                ))}
              </div>
            </aside>

            <SalaryHistoryPanel
              currentCycleId={selectedCycleId}
              employeeName={selectedEmployee?.employee_name}
              history={salaryHistory}
              isLoading={isHistoryLoading}
            />
          </div>
        ) : null}

        {resultView === 'versions' ? (
          <div className="mt-5 grid gap-5 xl:grid-cols-[360px_minmax(0,1fr)]">
            <aside className="surface-subtle px-5 py-5">
              <div className="section-head">
                <div>
                  <p className="eyebrow">方案版本</p>
                  <h3 className="section-title">保存当前试算</h3>
                  <p className="section-note">保存预算假设、筛选条件和员工试算结果。</p>
                </div>
                <span className="status-pill" style={{ background: 'var(--color-bg-subtle)', color: 'var(--color-ink)' }}>
                  {cycleVersions.length} 个版本
                </span>
              </div>

              <label className="mt-4 block">
                <span className="text-sm text-steel">版本名称</span>
                <input
                  className="toolbar-input mt-3 w-full"
                  onChange={(event) => setVersionNameInput(event.target.value)}
                  placeholder={selectedCycle ? createVersionName(selectedCycle.name, cycleVersions.length + 1) : '输入方案名称'}
                  value={versionNameInput}
                />
              </label>

              <div className="mt-4 grid gap-3">
                <button className="action-primary" disabled={!currentScenarioVersion} onClick={handleSaveVersion} type="button">
                  保存当前方案
                </button>
                <div className="surface px-4 py-3 text-sm text-steel">
                  <p>当前试算：{currentScenarioVersion ? currentScenarioVersion.cycleName : '暂无结果'}</p>
                  <p className="mt-2">
                    预算占用 {currentScenarioVersion ? `${(currentScenarioVersion.budgetUsageRate * 100).toFixed(1)}%` : '--'} / 手动覆盖{' '}
                    {currentScenarioVersion ? `${currentScenarioVersion.manualOverrideCount} 人` : '--'}
                  </p>
                </div>
              </div>

              {!cycleVersions.length ? (
                <div className="mt-5 rounded-[10px] border border-dashed border-[var(--color-border)] bg-white px-4 py-4 text-sm text-steel">
                  当前周期还没有保存的方案版本。
                </div>
              ) : (
                <div className="mt-5 space-y-3">
                  {cycleVersions.map((version) => (
                    <article className="surface px-4 py-4" key={version.id}>
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <h4 className="text-sm font-semibold text-ink">{version.name}</h4>
                          <p className="mt-1 text-xs text-steel">{formatDateTime(version.createdAt)}</p>
                        </div>
                        <span className="status-pill" style={{ background: 'var(--color-primary-light)', color: 'var(--color-primary)' }}>
                          {(version.budgetUsageRate * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="mt-4 grid gap-2 text-sm text-steel">
                        <div className="flex items-center justify-between gap-4">
                          <span>试算总额</span>
                          <span className="font-medium text-ink">{formatCurrency(version.recommendedCost)}</span>
                        </div>
                        <div className="flex items-center justify-between gap-4">
                          <span>平均调幅</span>
                          <span className="font-medium text-ink">{formatPercent(version.averageAdjustmentRate)}</span>
                        </div>
                        <div className="flex items-center justify-between gap-4">
                          <span>筛选条件</span>
                          <span className="font-medium text-ink">
                            {version.filters.department || '全部部门'} / {version.filters.jobFamily || '全部岗位族'}
                          </span>
                        </div>
                      </div>
                      <div className="mt-4 flex flex-wrap gap-2">
                        <button className="action-secondary" onClick={() => handleApplyVersion(version)} type="button">
                          载入沙盘
                        </button>
                        <button className="chip-button" onClick={() => setCompareLeftId(version.id)} type="button">
                          设为左侧
                        </button>
                        <button className="chip-button" onClick={() => setCompareRightId(version.id)} type="button">
                          设为右侧
                        </button>
                        <button className="chip-button" onClick={() => handleDeleteVersion(version.id)} type="button">
                          删除
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </aside>

            <section className="surface-subtle px-5 py-5">
              <div className="section-head">
                <div>
                  <p className="eyebrow">方案对比</p>
                  <h3 className="section-title">双方案差异</h3>
                  <p className="section-note">支持“当前试算 vs 已保存方案”或“两套已保存方案”对比。</p>
                </div>
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <label className="surface px-4 py-4">
                  <span className="text-sm text-steel">左侧方案</span>
                  <select className="toolbar-input mt-3 w-full" onChange={(event) => setCompareLeftId(event.target.value)} value={compareLeftId}>
                    {compareOptions.map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="surface px-4 py-4">
                  <span className="text-sm text-steel">右侧方案</span>
                  <select className="toolbar-input mt-3 w-full" onChange={(event) => setCompareRightId(event.target.value)} value={compareRightId}>
                    <option value="">请选择方案</option>
                    {compareOptions
                      .filter((option) => option.id !== compareLeftId)
                      .map((option) => (
                        <option key={option.id} value={option.id}>
                          {option.label}
                        </option>
                      ))}
                  </select>
                </label>
              </div>

              {!leftVersion || !rightVersion || !versionComparison ? (
                <div className="mt-5 rounded-[10px] border border-dashed border-[var(--color-border)] bg-white px-4 py-4 text-sm text-steel">
                  先保存至少一个方案版本，再选择左右方案进行对比。
                </div>
              ) : (
                <>
                  <div className="mt-5 grid gap-3 md:grid-cols-4">
                    {[
                      ['预算总额差异', formatCurrency(versionComparison.totalCostDelta), versionComparison.totalCostDelta >= 0 ? '右侧方案更高' : '右侧方案更低'],
                      ['平均调幅差异', formatDeltaPercent(versionComparison.averageAdjustmentDelta), '右侧方案减去左侧方案'],
                      ['预算使用率差异', formatDeltaPercent(versionComparison.budgetUsageDelta), '观察方案是否更接近预算上限'],
                      ['人工覆盖差异', `${versionComparison.manualOverrideDelta > 0 ? '+' : ''}${versionComparison.manualOverrideDelta}`, `${versionComparison.changedEmployees.length} 名员工出现变化`],
                    ].map(([label, value, note]) => (
                      <div className="surface px-4 py-4" key={label}>
                        <p className="text-xs uppercase tracking-[0.14em] text-placeholder">{label}</p>
                        <p className="mt-2 text-lg font-semibold text-ink">{value}</p>
                        <p className="mt-2 text-xs text-steel">{note}</p>
                      </div>
                    ))}
                  </div>

                  <div className="mt-5 grid gap-5 xl:grid-cols-[1.12fr_0.88fr]">
                    <section className="surface px-4 py-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-ink">员工差异</p>
                          <p className="mt-1 text-xs text-steel">
                            {leftVersion.name} 对比 {rightVersion.name}
                          </p>
                        </div>
                        <span className="status-pill" style={{ background: 'var(--color-bg-subtle)', color: 'var(--color-ink)' }}>
                          {versionComparison.changedEmployees.length} 项变化
                        </span>
                      </div>
                      <div className="table-shell mt-4">
                        <div className="overflow-x-auto">
                          <table className="table-lite">
                            <thead>
                              <tr>
                                <th>员工</th>
                                <th>左侧调幅</th>
                                <th>右侧调幅</th>
                                <th>涨薪差额</th>
                                <th>变化类型</th>
                              </tr>
                            </thead>
                            <tbody>
                              {versionComparison.changedEmployees.length ? (
                                versionComparison.changedEmployees.slice(0, 16).map((item) => (
                                  <tr key={item.employeeId}>
                                    <td>
                                      <div className="flex flex-col">
                                        <span className="font-medium text-ink">{item.employeeName}</span>
                                        <span className="text-xs text-steel">{item.department}</span>
                                      </div>
                                    </td>
                                    <td>{item.leftAdjustment == null ? '--' : formatPercent(item.leftAdjustment)}</td>
                                    <td>{item.rightAdjustment == null ? '--' : formatPercent(item.rightAdjustment)}</td>
                                    <td
                                      style={{
                                        color: item.deltaIncrease >= 0 ? 'var(--color-danger)' : 'var(--color-success)',
                                        fontWeight: 600,
                                      }}
                                    >
                                      {item.deltaIncrease > 0 ? '+' : ''}
                                      {formatCurrency(item.deltaIncrease)}
                                    </td>
                                    <td>{item.status}</td>
                                  </tr>
                                ))
                              ) : (
                                <tr>
                                  <td className="text-sm text-steel" colSpan={5}>
                                    当前两套方案没有员工层面的差异。
                                  </td>
                                </tr>
                              )}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </section>

                    <section className="surface px-4 py-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-ink">部门差异</p>
                          <p className="mt-1 text-xs text-steel">按部门观察预算增量和平均调幅变化。</p>
                        </div>
                      </div>
                      <div className="table-shell mt-4">
                        <div className="overflow-x-auto">
                          <table className="table-lite">
                            <thead>
                              <tr>
                                <th>部门</th>
                                <th>左侧总额</th>
                                <th>右侧总额</th>
                                <th>差额</th>
                                <th>平均调幅差异</th>
                              </tr>
                            </thead>
                            <tbody>
                              {versionComparison.departmentRows.length ? (
                                versionComparison.departmentRows.map((item) => (
                                  <tr key={item.department}>
                                    <td>{item.department}</td>
                                    <td>{formatCurrency(item.leftTotalIncrease)}</td>
                                    <td>{formatCurrency(item.rightTotalIncrease)}</td>
                                    <td
                                      style={{
                                        color: item.deltaIncrease >= 0 ? 'var(--color-danger)' : 'var(--color-success)',
                                        fontWeight: 600,
                                      }}
                                    >
                                      {item.deltaIncrease > 0 ? '+' : ''}
                                      {formatCurrency(item.deltaIncrease)}
                                    </td>
                                    <td>{formatDeltaPercent(item.deltaAverageAdjustment)}</td>
                                  </tr>
                                ))
                              ) : (
                                <tr>
                                  <td className="text-sm text-steel" colSpan={5}>
                                    当前两套方案没有部门层面的差异。
                                  </td>
                                </tr>
                              )}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </section>
                  </div>
                </>
              )}
            </section>
          </div>
        ) : null}
      </section>
    </AppShell>
  );
}
