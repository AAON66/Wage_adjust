import { useId, useState } from 'react';

interface FileUploadPanelProps {
  isGithubImporting?: boolean;
  isUploading: boolean;
  onFilesSelected: (files: FileList | null) => void;
  onGitHubImport?: (url: string) => void;
}

export function FileUploadPanel({ isGithubImporting = false, isUploading, onFilesSelected, onGitHubImport }: FileUploadPanelProps) {
  const inputId = useId();
  const [githubUrl, setGitHubUrl] = useState('');

  return (
    <section className="surface-subtle px-6 py-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="eyebrow">材料上传</p>
          <h3 className="section-title">上传员工材料</h3>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-steel">
            支持本地文件上传，也可以直接导入 GitHub 仓库、分支目录或文件链接做解析。上传后文件可继续替换或移除，当前单文件上限为 200MB。
          </p>
        </div>
        <label className={isUploading ? 'action-secondary cursor-pointer' : 'action-primary cursor-pointer'} htmlFor={inputId}>
          {isUploading ? '上传中...' : '选择文件'}
        </label>
      </div>
      <input
        accept=".ppt,.pptx,.pdf,.docx,.png,.jpg,.jpeg,.zip,.md,.xlsx,.xls,.py,.ts,.tsx,.js,.json,.txt,.yml,.yaml"
        className="sr-only"
        id={inputId}
        multiple
        onChange={(event) => {
          onFilesSelected(event.target.files);
          event.currentTarget.value = '';
        }}
        type="file"
      />
      <div className="mt-5 grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto]">
        <input
          className="toolbar-input"
          onChange={(event) => setGitHubUrl(event.target.value)}
          placeholder="粘贴 GitHub 链接，例如仓库、目录或文件地址"
          type="url"
          value={githubUrl}
        />
        <button
          className="action-secondary"
          disabled={!onGitHubImport || isGithubImporting || !githubUrl.trim()}
          onClick={() => {
            onGitHubImport?.(githubUrl.trim());
            setGitHubUrl('');
          }}
          type="button"
        >
          {isGithubImporting ? '导入中...' : '导入 GitHub 链接'}
        </button>
      </div>
      <div className="mt-5 flex flex-wrap gap-2 text-xs text-steel">
        {['PPT', 'PDF', 'DOCX', 'PNG', 'JPG', 'ZIP', 'Markdown', 'Excel', '代码', 'GitHub 仓库/目录/文件'].map((item) => (
          <span key={item} className="chip-button px-3 py-1 text-xs">
            {item}
          </span>
        ))}
      </div>
      <p className="mt-4 text-xs leading-6 text-steel">
        如果仍然提示超限，请先压缩图片、精简导出页数，或把大型项目材料拆分成多个文件上传。
      </p>
    </section>
  );
}

