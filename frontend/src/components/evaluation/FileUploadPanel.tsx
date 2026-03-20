import { useId } from 'react';

interface FileUploadPanelProps {
  isUploading: boolean;
  onFilesSelected: (files: FileList | null) => void;
}

export function FileUploadPanel({ isUploading, onFilesSelected }: FileUploadPanelProps) {
  const inputId = useId();

  return (
    <section className="rounded-[28px] border border-dashed border-slate-300 bg-slate-50 p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-[0.24em] text-ember">File Upload</p>
          <h3 className="mt-2 text-2xl font-bold text-ink">Drop in employee materials</h3>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
            This UI is ready for PPT, PDF, image, code, markdown, and spreadsheet uploads. Backend upload APIs will plug into the same panel next.
          </p>
        </div>
        <label className={`inline-flex cursor-pointer items-center rounded-full px-5 py-3 text-sm font-semibold ${isUploading ? 'bg-slate-300 text-slate-600' : 'bg-ink text-white'}`} htmlFor={inputId}>
          {isUploading ? 'Uploading...' : 'Select files'}
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
      <div className="mt-5 flex flex-wrap gap-2 text-xs text-slate-500">
        {['PPT', 'PDF', 'PNG', 'JPG', 'ZIP', 'Markdown', 'Excel', 'Code'].map((item) => (
          <span key={item} className="rounded-full bg-white px-3 py-1 shadow-sm">
            {item}
          </span>
        ))}
      </div>
    </section>
  );
}