import { useId } from 'react';

interface FileUploadPanelProps {
  isUploading: boolean;
  onFilesSelected: (files: FileList | null) => void;
}

export function FileUploadPanel({ isUploading, onFilesSelected }: FileUploadPanelProps) {
  const inputId = useId();

  return (
    <section className="surface-subtle px-6 py-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="eyebrow">材料上传</p>
          <h3 className="section-title">上传员工材料</h3>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-steel">
            当前支持 PPT、PDF、图片、代码、Markdown 和表格材料上传，上传后会进入解析和证据抽取链路。
          </p>
        </div>
        <label className={isUploading ? 'action-secondary cursor-pointer' : 'action-primary cursor-pointer'} htmlFor={inputId}>
          {isUploading ? '上传中...' : '选择文件'}
        </label>
      </div>
      <input
        accept=".ppt,.pptx,.pdf,.png,.jpg,.jpeg,.zip,.md,.xlsx,.xls,.py,.ts,.tsx,.js"
        className="sr-only"
        id={inputId}
        multiple
        onChange={(event) => onFilesSelected(event.target.files)}
        type="file"
      />
      <div className="mt-5 flex flex-wrap gap-2 text-xs text-steel">
        {['PPT', 'PDF', 'PNG', 'JPG', 'ZIP', 'Markdown', 'Excel', '代码'].map((item) => (
          <span key={item} className="chip-button px-3 py-1 text-xs">
            {item}
          </span>
        ))}
      </div>
    </section>
  );
}
