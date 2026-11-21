"use client";

import { useCallback, useEffect, useState } from "react";
import { DashboardFrame } from "@/components/bi/DashboardFrame";
import { KpiCard } from "@/components/bi/KpiCard";
import { BiChart } from "@/components/bi/BiChart";
import { ErrorState } from "@/components/bi/ErrorState";
import { EmptyState } from "@/components/bi/EmptyState";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { activeFilters, useRestaurantFilters } from "@/lib/filters";
import {
  formatCurrency,
  formatNumber,
  restaurantApi,
  type InsightItem,
  type KpiData,
  type TrendPoint,
} from "@/lib/restaurant";

export default function OverviewPage() {
  const { token, logout } = useAuth();
  const { filters } = useRestaurantFilters();
  const [kpis, setKpis] = useState<KpiData | null>(null);
  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [insights, setInsights] = useState<InsightItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [queryMs, setQueryMs] = useState<number | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    const f = activeFilters(filters);
    try {
      const [kpiRes, trendRes, insightRes] = await Promise.all([
        restaurantApi.kpis(token, f),
        restaurantApi.trends(token, f, "day"),
        restaurantApi.insights(token, f),
      ]);
      setKpis(kpiRes.data);
      setTrends(trendRes.data);
      setInsights(insightRes.data);
      setQueryMs(kpiRes.meta?.query_ms ?? null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        logout();
        return;
      }
      setError(err instanceof ApiError ? err.message : "Failed to load overview.");
    } finally {
      setLoading(false);
    }
  }, [token, filters, logout]);

  useEffect(() => {
    load();
  }, [load]);

  const growth = kpis?.comparison?.growth;

  return (
    <DashboardFrame
      title="Overview"
      subtitle="California Burrito Analytics — revenue, orders and outlet snapshot"
    >
      {error && <ErrorState message={error} onRetry={load} />}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <KpiCard
          label="Total Revenue"
          value={formatCurrency(kpis?.total_revenue ?? 0)}
          growthPct={growth?.total_revenue_pct}
          loading={loading}
          accent="blue"
        />
        <KpiCard
          label="Total Orders"
          value={formatNumber(kpis?.total_orders ?? 0)}
          growthPct={growth?.total_orders_pct}
          loading={loading}
          accent="orange"
        />
        <KpiCard
          label="Average Order Value"
          value={formatCurrency(kpis?.aov ?? 0)}
          growthPct={growth?.aov_pct}
          loading={loading}
        />
        <KpiCard
          label="Total Items Sold"
          value={formatNumber(kpis?.total_items_sold ?? 0)}
          loading={loading}
          accent="slate"
        />
        <KpiCard
          label="Transaction Records"
          value={formatNumber(kpis?.total_transactions ?? 0)}
          loading={loading}
        />
        <KpiCard
          label="Active Outlets"
          value={formatNumber(kpis?.active_outlets ?? 0)}
          loading={loading}
          accent="orange"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-5">
        <div className="bi-card p-5 lg:col-span-3">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
              Daily revenue trend
            </h2>
            {queryMs !== null && (
              <span className="text-[11px] text-slate-400">{queryMs} ms</span>
            )}
          </div>
          {!loading && (kpis?.total_transactions ?? 0) === 0 ? (
            <EmptyState />
          ) : (
            <BiChart
              type="area"
              labels={trends.map((t) => t.period || "")}
              values={trends.map((t) => t.revenue)}
              seriesName="Revenue"
            />
          )}
        </div>
        <div className="bi-card p-5 lg:col-span-2">
          <h2 className="mb-3 text-sm font-semibold text-slate-800 dark:text-slate-100">
            Business insights
          </h2>
          <div className="space-y-3">
            {insights.length === 0 && !loading && (
              <p className="text-sm text-slate-500">No insights available.</p>
            )}
            {insights.map((item) => (
              <div
                key={item.title}
                className="rounded-xl border border-slate-100 bg-slate-50/80 p-3 dark:border-slate-800 dark:bg-slate-900/60"
              >
                <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700 dark:text-emerald-300">
                  {item.title}
                </p>
                <p className="mt-1 text-sm text-slate-700 dark:text-slate-300">{item.detail}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </DashboardFrame>
  );
}
