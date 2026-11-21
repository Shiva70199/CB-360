"use client";

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="bi-card border-rose-200 bg-rose-50/60 p-5 dark:border-rose-900 dark:bg-rose-950/40">
      <p className="text-sm font-medium text-rose-700 dark:text-rose-300">{message}</p>
      {onRetry && (
        <button type="button" onClick={onRetry} className="bi-btn-secondary mt-3">
          Retry
        </button>
      )}
    </div>
  );
}
