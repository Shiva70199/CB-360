"use client";

export function EmptyState({
  title = "No data yet",
  detail = "Import restaurant transactions from Data Management to populate this view.",
}: {
  title?: string;
  detail?: string;
}) {
  return (
    <div className="bi-card flex flex-col items-center justify-center px-6 py-14 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
          <path
            d="M4 19h16M7 16V9m5 7V5m5 11v-4"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
      </div>
      <h3 className="mt-4 text-base font-semibold text-slate-900 dark:text-white">{title}</h3>
      <p className="mt-2 max-w-md text-sm text-slate-500 dark:text-slate-400">{detail}</p>
    </div>
  );
}
