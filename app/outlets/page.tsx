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
  formatNumber,
  restaurantApi,
  type NamedRevenueRow,
} from "@/lib/restaurant";

export default function OutletsPage() {
  const { token, logout } = useAuth();
  const { filters } = useRestaurantFilters();
  const [rows, setRows] = useState<NamedRevenueRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await restaurantApi.outlets(token, activeFilters(filters));
      setRows(res.data);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        logout();
        return;
      }
      setError(err instanceof ApiError ? err.message : "Failed to load outlets.");
    } finally {
      setLoading(false);
    }
  }, [token, filters, logout]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <DashboardFrame title="Outlet Performance" subtitle="Compare revenue, orders and average order value by outlet">
      {error && <ErrorState message={error} onRetry={load} />}

      <div className="bi-card p-5">
        <h2 className="mb-3 text-sm font-semibold">Revenue by outlet</h2>
        <BiChart
          type="bar"
          labels={rows.map((r) => r.name || "")}
          values={rows.map((r) => r.revenue)}
          height={340}
        />
      </div>

      <div className="bi-card overflow-hidden">
        <div className="border-b border-slate-100 px-5 py-4 dark:border-slate-800">
          <h2 className="text-sm font-semibold">Outlet leaderboard</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="bi-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Outlet</th>
                <th>Revenue</th>
                <th>Orders</th>
                <th>AOV</th>
                <th>Items sold</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, idx) => (
                <tr key={row.name || idx}>
                  <td>{idx + 1}</td>
                  <td className="font-medium">{row.name}</td>
                  <td>{formatCurrency(row.revenue)}</td>
                  <td>{formatNumber(row.orders)}</td>
                  <td>{formatCurrency(row.aov || 0)}</td>
                  <td>{formatNumber(row.items_sold || 0)}</td>
                </tr>
              ))}
              {!loading && rows.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-10 text-center text-slate-500">
                    No outlet data for current filters.
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
