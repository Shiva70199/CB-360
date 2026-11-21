"use client";

export function LoadingSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: Math.min(rows, 6) }).map((_, i) => (
          <div key={i} className="h-28 animate-pulse rounded-xl bg-slate-200/80 dark:bg-slate-800" />
        ))}
      </div>
      <div className="h-72 animate-pulse rounded-xl bg-slate-200/80 dark:bg-slate-800" />
    </div>
  );
}
