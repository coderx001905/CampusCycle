import React from 'react';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

export const NotificationToast = ({ toast, onClose }) => {
  if (!toast) return null;

  const { type = 'info', message, title } = toast;

  const icons = {
    success: <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />,
    error: <AlertCircle className="w-5 h-5 text-rose-500 shrink-0" />,
    info: <Info className="w-5 h-5 text-blue-500 shrink-0" />,
  };

  const borders = {
    success: 'border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/80',
    error: 'border-rose-200 dark:border-rose-800 bg-rose-50 dark:bg-rose-950/80',
    info: 'border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/80',
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 max-w-sm w-full animate-in slide-in-from-bottom-5 duration-300">
      <div className={`p-4 rounded-xl border shadow-xl flex items-start gap-3 ${borders[type] || borders.info}`}>
        {icons[type] || icons.info}
        <div className="flex-1 min-w-0">
          {title && <h4 className="text-sm font-semibold text-slate-900 dark:text-white">{title}</h4>}
          <p className="text-xs text-slate-700 dark:text-slate-300 mt-0.5">{message}</p>
        </div>
        <button
          onClick={onClose}
          className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

export default NotificationToast;
