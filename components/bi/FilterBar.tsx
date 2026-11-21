"use client";

import { activeFilters, useRestaurantFilters } from "@/lib/filters";

export function FilterBar() {
  const { filters, options, loadingOptions, setFilter, clearAll } = useRestaurantFilters();
  const activeCount = Object.keys(activeFilters(filters)).length;

  const selectClass =
    "bi-select min-w-[140px]";

  return (
    <div className="bi-card space-y-3 p-4">
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-xs font-medium text-slate-500">
          From
          <input
            type="date"
            className="bi-input"
            value={filters.date_from || ""}
            onChange={(e) => setFilter("date_from", e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-slate-500">
          To
          <input
            type="date"
            className="bi-input"
            value={filters.date_to || ""}
            onChange={(e) => setFilter("date_to", e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-slate-500">
          Brand
          <select
            className={selectClass}
            value={filters.brand || ""}
            onChange={(e) => setFilter("brand", e.target.value)}
            disabled={loadingOptions}
          >
            <option value="">All brands</option>
            {(options?.brands || []).map((b) => (
              <option key={b} value={b}>
                {b}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-slate-500">
          Outlet
          <select
            className={selectClass}
            value={filters.outlet || ""}
            onChange={(e) => setFilter("outlet", e.target.value)}
            disabled={loadingOptions}
          >
            <option value="">All outlets</option>
            {(options?.outlets || []).map((o) => (
              <option key={o} value={o}>
                {o}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-slate-500">
          Category
          <select
            className={selectClass}
            value={filters.menu_group || ""}
            onChange={(e) => setFilter("menu_group", e.target.value)}
            disabled={loadingOptions}
          >
            <option value="">All categories</option>
            {(options?.menu_groups || []).map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-slate-500">
          Order type
          <select
            className={selectClass}
            value={filters.order_type || ""}
            onChange={(e) => setFilter("order_type", e.target.value)}
            disabled={loadingOptions}
          >
            <option value="">All types</option>
            {(options?.order_types || []).map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-slate-500">
          Settlement
          <select
            className={selectClass}
            value={filters.settlement || ""}
            onChange={(e) => setFilter("settlement", e.target.value)}
            disabled={loadingOptions}
          >
            <option value="">All settlements</option>
            {(options?.settlements || []).map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <button type="button" onClick={clearAll} className="bi-btn-secondary">
          Clear{activeCount ? ` (${activeCount})` : ""}
        </button>
      </div>
      {options?.date_min && options?.date_max && (
        <p className="text-[11px] text-slate-400">
          Data range: {options.date_min.slice(0, 10)} → {options.date_max.slice(0, 10)}
        </p>
      )}
    </div>
  );
}
