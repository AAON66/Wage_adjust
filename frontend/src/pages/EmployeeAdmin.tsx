import axios from 'axios';
import { useEffect, useMemo, useState } from 'react';

import { AppShell } from '../components/layout/AppShell';
import { useAuth } from '../hooks/useAuth';
import { fetchEmployees } from '../services/employeeService';
import { deleteHandbook, fetchHandbooks, uploadHandbook } from '../services/handbookService';
import { fetchUsers, updateManagedUserEmployeeBinding } from '../services/userAdminService';
import type { EmployeeHandbookRecord, EmployeeRecord, UserProfile } from '../types/api';
import { getRoleLabel } from '../utils/roleAccess';

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as { detail?: string; message?: string; details?: Array<{ loc?: Array<string | number>; msg?: string }> } | undefined;
    const firstDetail = data?.details?.[0];
    if (firstDetail?.loc?.includes('page_size')) {
      return '请求数量超过系统允许范围，请缩小查询数量后重试。';
    }
    return data?.detail ?? data?.message ?? firstDetail?.msg ?? '员工档案管理操作失败。';
  }
  return '员工档案管理操作失败。';
}

function formatBindingKeyword(employee: EmployeeRecord | null | undefined): string {
  if (!employee) {
    return '';
  }
  return `${employee.name}${employee.employee_no ? ` ${employee.employee_no}` : ''}`.trim();
}

export function EmployeeAdminPage() {
  const { user } = useAuth();
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [employees, setEmployees] = useState<EmployeeRecord[]>([]);
  const [handbooks, setHandbooks] = useState<EmployeeHandbookRecord[]>([]);
  const [keyword, setKeyword] = useState('');
  const [bindingDrafts, setBindingDrafts] = useState<Record<string, string>>({});
  const [bindingSearchDrafts, setBindingSearchDrafts] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isUploadingHandbook, setIsUploadingHandbook] = useState(false);
  const [workingUserId, setWorkingUserId] = useState<string | null>(null);
  const [deletingHandbookId, setDeletingHandbookId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  async function loadPageData() {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const [userResponse, employeeResponse, handbookResponse] = await Promise.all([
        fetchUsers({ page: 1, page_size: 100 }),
        fetchEmployees({ page: 1, page_size: 100 }),
        fetchHandbooks(),
      ]);
      setUsers(userResponse.items);
      setEmployees(employeeResponse.items);
      setHandbooks(handbookResponse.items);
      setBindingDrafts(Object.fromEntries(userResponse.items.map((item) => [item.id, item.employee_id ?? ''])));
      setBindingSearchDrafts(
        Object.fromEntries(
          userResponse.items.map((item) => [
            item.id,
            item.employee_id ? `${item.employee_name ?? ''}${item.employee_no ? ` ${item.employee_no}` : ''}`.trim() : '',
          ]),
        ),
      );
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadPageData();
  }, []);

  const manageableUsers = useMemo(() => {
    const loweredKeyword = keyword.trim().toLowerCase();
    return users
      .filter((item) => item.id !== user?.id)
      .filter((item) => {
        if (!loweredKeyword) return true;
        return [item.email, item.employee_name ?? '', item.employee_no ?? ''].some((value) => value.toLowerCase().includes(loweredKeyword));
      });
  }, [keyword, user?.id, users]);

  const unboundEmployees = useMemo(() => employees.filter((employee) => !employee.bound_user_id), [employees]);
  const boundUsersCount = useMemo(() => users.filter((item) => item.employee_id).length, [users]);

  function getEmployeeOptionsForUser(targetUser: UserProfile): EmployeeRecord[] {
    return employees.filter((employee) => !employee.bound_user_id || employee.bound_user_id === targetUser.id);
  }

  function getFilteredEmployeeOptions(targetUser: UserProfile): EmployeeRecord[] {
    const searchValue = (bindingSearchDrafts[targetUser.id] ?? '').trim().toLowerCase();
    const options = getEmployeeOptionsForUser(targetUser);
    if (!searchValue) {
      return options;
    }
    return options.filter((employee) =>
      [employee.name, employee.employee_no, employee.department, employee.job_family]
        .filter(Boolean)
        .some((value) => value.toLowerCase().includes(searchValue)),
    );
  }

  async function handleSaveBinding(targetUser: UserProfile) {
    const nextEmployeeId = bindingDrafts[targetUser.id] || null;
    setWorkingUserId(targetUser.id);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const updatedUser = await updateManagedUserEmployeeBinding(targetUser.id, nextEmployeeId);
      setUsers((current) => current.map((item) => item.id === updatedUser.id ? updatedUser : item));
      setEmployees((current) => current.map((employee) => {
        if (employee.id === updatedUser.employee_id) {
          return {
            ...employee,
            bound_user_id: updatedUser.id,
            bound_user_email: updatedUser.email,
          };
        }
        if (employee.bound_user_id === updatedUser.id && employee.id !== updatedUser.employee_id) {
          return {
            ...employee,
            bound_user_id: null,
            bound_user_email: null,
          };
        }
        return employee;
      }));
      setBindingSearchDrafts((current) => ({
        ...current,
        [targetUser.id]: nextEmployeeId ? formatBindingKeyword(employees.find((employee) => employee.id === nextEmployeeId)) : '',
      }));
      setSuccessMessage(nextEmployeeId ? '员工档案绑定已更新。' : '员工档案绑定已解除。');
      await loadPageData();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setWorkingUserId(null);
    }
  }

  async function handleUploadHandbook(fileList: globalThis.FileList | null) {
    const file = fileList?.[0];
    if (!file) {
      return;
    }

    setIsUploadingHandbook(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await uploadHandbook(file);
      setSuccessMessage('员工手册已上传并完成解析。');
      await loadPageData();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsUploadingHandbook(false);
    }
  }

  async function handleDeleteHandbook(handbook: EmployeeHandbookRecord) {
    if (!window.confirm(`确认删除手册《${handbook.title}》吗？`)) {
      return;
    }

    setDeletingHandbookId(handbook.id);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await deleteHandbook(handbook.id);
      setSuccessMessage('员工手册已删除。');
      setHandbooks((current) => current.filter((item) => item.id !== handbook.id));
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setDeletingHandbookId(null);
    }
  }

  return (
    <AppShell
      title="员工档案与手册"
      description="在这里完成平台账号与员工档案的一对一绑定，并维护面向公司内部使用的员工手册解析库。"
      actions={<span className="rounded-full bg-[#edf3ff] px-4 py-2 text-sm text-[#2750b6]">当前身份：{getRoleLabel(user?.role)}</span>}
    >
      <section className="metric-strip animate-fade-up">
        {[
          ['员工档案', String(employees.length), '系统内可用于绑定的员工档案数量。'],
          ['已完成绑定', String(boundUsersCount), '已有平台账号绑定正式员工档案。'],
          ['待绑定档案', String(unboundEmployees.length), '这些员工档案还没有关联平台账号。'],
          ['员工手册', String(handbooks.length), '已上传并纳入后台解析的制度文档数量。'],
        ].map(([label, value, note]) => (
          <article className="metric-tile" key={label}>
            <p className="metric-label">{label}</p>
            <p className="metric-value text-[26px]">{value}</p>
            <p className="metric-note">{note}</p>
          </article>
        ))}
      </section>

      {errorMessage ? <p className="surface px-5 py-4 text-sm text-red-600">{errorMessage}</p> : null}
      {successMessage ? <p className="surface px-5 py-4 text-sm text-emerald-700">{successMessage}</p> : null}
      {isLoading ? <p className="surface px-5 py-4 text-sm text-steel">正在加载员工档案管理数据...</p> : null}

      <section className="grid gap-5 xl:grid-cols-[1.08fr_0.92fr]">
        <section className="surface px-6 py-6 lg:px-7">
          <div className="section-head">
            <div>
              <p className="eyebrow">档案绑定</p>
              <h2 className="section-title">平台账号与员工档案</h2>
              <p className="section-note mt-2">正式绑定后，员工个人评估中心会优先按数据库绑定关系识别，不再依赖演示映射。</p>
            </div>
          </div>

          <div className="mt-5 grid gap-3 lg:grid-cols-[minmax(0,1fr)_220px]">
            <input
              className="toolbar-input"
              onChange={(event) => setKeyword(event.target.value)}
              placeholder="按邮箱、员工姓名或工号搜索"
              value={keyword}
            />
            <div className="surface-subtle px-4 py-4 text-sm text-steel">只展示你当前权限范围内可管理的账号，不会显示你自己。</div>
          </div>

          <div className="mt-5 grid gap-4">
            {manageableUsers.map((item) => {
              const options = getFilteredEmployeeOptions(item);
              const isWorking = workingUserId === item.id;
              return (
                <article className="list-row p-5" key={item.id}>
                  <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px_280px_auto] lg:items-end">
                    <div>
                      <div className="flex flex-wrap items-center gap-3">
                        <h3 className="text-base font-semibold text-ink">{item.email}</h3>
                        <span className="status-pill bg-[#edf3ff] text-[#2750b6]">{getRoleLabel(item.role)}</span>
                      </div>
                      <p className="mt-2 text-sm text-steel">
                        {item.employee_id ? `当前绑定：${item.employee_name ?? '未命名员工'}${item.employee_no ? `（${item.employee_no}）` : ''}` : '当前尚未绑定员工档案。'}
                      </p>
                    </div>
                    <label className="grid gap-2 text-sm text-ink">
                      <span>搜索员工档案</span>
                      <input
                        className="toolbar-input"
                        disabled={isWorking}
                        onChange={(event) => setBindingSearchDrafts((current) => ({ ...current, [item.id]: event.target.value }))}
                        placeholder="输入姓名、工号、部门或岗位"
                        value={bindingSearchDrafts[item.id] ?? ''}
                      />
                    </label>
                    <label className="grid gap-2 text-sm text-ink">
                      <span>选择员工档案</span>
                      <select
                        className="toolbar-input"
                        disabled={isWorking}
                        onChange={(event) => {
                          const nextEmployeeId = event.target.value;
                          const selectedEmployee = employees.find((employee) => employee.id === nextEmployeeId);
                          setBindingDrafts((current) => ({ ...current, [item.id]: nextEmployeeId }));
                          setBindingSearchDrafts((current) => ({
                            ...current,
                            [item.id]: selectedEmployee ? formatBindingKeyword(selectedEmployee) : '',
                          }));
                        }}
                        value={bindingDrafts[item.id] ?? ''}
                      >
                        <option value="">暂不绑定</option>
                        {options.map((employee) => (
                          <option key={employee.id} value={employee.id}>{employee.name} · {employee.employee_no}</option>
                        ))}
                      </select>
                      <span className="text-xs text-steel">当前可选 {options.length} 条员工档案</span>
                    </label>
                    <button className="action-primary" disabled={isWorking} onClick={() => void handleSaveBinding(item)} type="button">
                      {isWorking ? '保存中...' : '保存绑定'}
                    </button>
                  </div>
                </article>
              );
            })}
            {!manageableUsers.length ? <p className="text-sm text-steel">当前没有可管理的账号可用于员工档案绑定。</p> : null}
          </div>
        </section>

        <section className="surface px-6 py-6 lg:px-7">
          <div className="section-head">
            <div>
              <p className="eyebrow">员工手册</p>
              <h2 className="section-title">上传并解析制度文档</h2>
              <p className="section-note mt-2">支持上传公司内部员工手册，系统会用解析链路提取摘要、重点条款和主题标签。</p>
            </div>
          </div>

          <div className="surface-subtle mt-5 px-5 py-5">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-ink">上传新手册</p>
                <p className="mt-2 text-sm leading-6 text-steel">当前支持 PDF、Markdown、TXT。上传后会自动调用本地解析链路，并在已配置 DeepSeek 时优先使用大模型结构化输出。</p>
              </div>
              <label className={isUploadingHandbook ? 'action-secondary cursor-pointer' : 'action-primary cursor-pointer'}>
                {isUploadingHandbook ? '上传中...' : '选择手册文件'}
                <input
                  accept=".pdf,.md,.txt"
                  className="sr-only"
                  onChange={(event) => {
                    void handleUploadHandbook(event.target.files);
                    event.currentTarget.value = '';
                  }}
                  type="file"
                />
              </label>
            </div>
          </div>

          <div className="mt-5 grid gap-4">
            {handbooks.map((handbook) => (
              <article className="list-row p-5" key={handbook.id}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h3 className="text-base font-semibold text-ink">{handbook.title}</h3>
                    <p className="mt-1 text-sm text-steel">{handbook.file_name} · {handbook.file_type.toUpperCase()} · {new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(handbook.created_at))}</p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="status-pill bg-emerald-50 text-emerald-700">{handbook.parse_status === 'parsed' ? '已解析' : handbook.parse_status}</span>
                    <button className="action-danger px-4 py-2 text-xs" disabled={deletingHandbookId === handbook.id} onClick={() => void handleDeleteHandbook(handbook)} type="button">
                      {deletingHandbookId === handbook.id ? '删除中...' : '删除'}
                    </button>
                  </div>
                </div>
                <p className="mt-4 text-sm leading-6 text-steel">{handbook.summary ?? '当前尚未生成摘要。'}</p>
                {handbook.key_points_json.length ? (
                  <div className="mt-4 grid gap-2">
                    {handbook.key_points_json.map((point) => (
                      <div className="surface-subtle px-4 py-3 text-sm leading-6 text-ink" key={point}>{point}</div>
                    ))}
                  </div>
                ) : null}
                {handbook.tags_json.length ? (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {handbook.tags_json.map((tag) => (
                      <span className="chip-button" key={tag}>{tag}</span>
                    ))}
                  </div>
                ) : null}
              </article>
            ))}
            {!handbooks.length ? <p className="text-sm text-steel">当前还没有上传员工手册。</p> : null}
          </div>
        </section>
      </section>
    </AppShell>
  );
}
