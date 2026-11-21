"use client";

import { useCallback, useEffect, useState } from "react";
import { DashboardFrame } from "@/components/bi/DashboardFrame";
import { BiChart } from "@/components/bi/BiChart";
import { ErrorState } from "@/components/bi/ErrorState";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { activeFilters, useRestaurantFilters } from "@/lib/filters";
import {
  formatCurrency,
  restaurantApi,
  type NamedRevenueRow,
  type ProductRow,
  type TrendPoint,
} from "@/lib/restaurant";
import clsx from "clsx";

type Granularity = "day" | "week" | "month";

export default function SalesPage() {
  const { token, logout } = useAuth();
  const { filters } = useRestaurantFilters();
  const [granularity, setGranularity] = useState<Granularity>("day");
  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [outlets, setOutlets] = useState<NamedRevenueRow[]>([]);
  const [brands, setBrands] = useState<NamedRevenueRow[]>([]);
  const [categories, setCategories] = useState<NamedRevenueRow[]>([]);
  const [topItems, setTopItems] = useState<ProductRow[]>([]);
  const [contribution, setContribution] = useState<ProductRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    const f = activeFilters(filters);
    try {
      const [t, o, b, c, p] = await Promise.all([
        restaurantApi.trends(token, f, granularity),
        restaurantApi.outlets(token, f),
        restaurantApi.brands(token, f),
        restaurantApi.categories(token, f),
        restaurantApi.productContribution(token, f, 10),
      ]);
      setTrends(t.data);
      setOutlets(o.data);
      setBrands(b.data);
      setCategories(c.data);
      setTopItems(p.data.top_items || []);
      setContribution(p.data.contribution || []);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        logout();
        return;
      }
      setError(err instanceof ApiError ? err.message : "Failed to load sales analytics.");
    } finally {
      setLoading(false);
    }
  }, [token, filters, granularity, logout]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <DashboardFrame title="Sales Analytics" subtitle="Revenue trends and contribution across the California Burrito workspace">
      {error && <ErrorState message={error} onRetry={load} />}

      <div className="bi-card p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-sm font-semibold">Revenue trend</h2>
          <div className="flex rounded-full bg-slate-100 p-1 dark:bg-slate-800">
            {(["day", "week", "month"] as Granularity[]).map((g) => (
              <button
                key={g}
                type="button"
                onClick={() => setGranularity(g)}
                className={clsx(
                  "rounded-full px-3 py-1 text-xs font-semibold capitalize transition",
                  granularity === g
                    ? "bg-emerald-800 text-white"
                    : "text-slate-600 hover:text-slate-900 dark:text-slate-300"
                )}
              >
                {g === "day" ? "Daily" : g === "week" ? "Weekly" : "Monthly"}
              </button>
            ))}
          </div>
        </div>
        <BiChart
          type="line"
          labels={trends.map((t) => t.period || "")}
          values={trends.map((t) => t.revenue)}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="bi-card p-5">
          <h2 className="mb-3 text-sm font-semibold">Revenue by outlet</h2>
          <BiChart
            type="bar"
            labels={outlets.map((r) => r.name || "")}
            values={outlets.map((r) => r.revenue)}
          />
        </div>
        <div className="bi-card p-5">
          <h2 className="mb-3 text-sm font-semibold">Revenue by brand</h2>
          <BiChart
            type="bar"
            labels={brands.map((r) => r.name || "")}
            values={brands.map((r) => r.revenue)}
          />
        </div>
        <div className="bi-card p-5">
          <h2 className="mb-3 text-sm font-semibold">Revenue by menu category</h2>
          <BiChart
            type="donut"
            labels={categories.map((r) => r.name || "")}
            values={categories.map((r) => r.revenue)}
          />
        </div>
        <div className="bi-card p-5">
          <h2 className="mb-3 text-sm font-semibold">Top 10 selling items</h2>
          <BiChart
            type="bar"
            labels={topItems.map((r) => r.item || "")}
            values={topItems.map((r) => r.revenue)}
          />
        </div>
      </div>

      <div className="bi-card overflow-hidden">
        <div className="border-b border-slate-100 px-5 py-4 dark:border-slate-800">
          <h2 className="text-sm font-semibold">Product revenue contribution</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="bi-table">
            <thead>
              <tr>
                <th>Item</th>
                <th>Category</th>
                <th>Revenue</th>
                <th>Contribution</th>
              </tr>
            </thead>
            <tbody>
              {contribution.map((row) => (
                <tr key={`${row.item}-${row.menu_group}`}>
                  <td>{row.item}</td>
                  <td>{row.menu_group}</td>
                  <td>{formatCurrency(row.revenue)}</td>
                  <td>{(row.contribution_pct ?? 0).toFixed(1)}%</td>
                </tr>
              ))}
              {!loading && contribution.length === 0 && (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-slate-500">
                    No contribution data for current filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </DashboardFrame>
  );
}
