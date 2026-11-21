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

export default function PaymentsPage() {
  const { token, logout } = useAuth();
  const { filters } = useRestaurantFilters();
  const [rows, setRows] = useState<NamedRevenueRow[]>([]);
  const [outletWise, setOutletWise] = useState<
    { outlet: string | null; settlement: string | null; revenue: number; orders: number }[]
  >([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await restaurantApi.settlements(token, activeFilters(filters));
      setRows(res.data.distribution || []);
      setOutletWise(res.data.outlet_wise || []);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        logout();
        return;
      }
      setError(err instanceof ApiError ? err.message : "Failed to load payment analytics.");
    } finally {
      setLoading(false);
    }
  }, [token, filters, logout]);

  useEffect(() => {
    load();
  }, [load]);

  const totalRevenue = rows.reduce((s, r) => s + r.revenue, 0);

  return (
    <DashboardFrame
      title="Payment Analytics"
      subtitle="Payment methods and settlement mix from imported transactions"
    >
      {error && <ErrorState message={error} onRetry={load} />}

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="bi-card p-5">
          <h2 className="mb-3 text-sm font-semibold">Settlement distribution</h2>
          <BiChart
            type="donut"
            labels={rows.map((r) => r.name || "")}
            values={rows.map((r) => r.revenue)}
          />
        </div>
        <div className="bi-card p-5">
          <h2 className="mb-3 text-sm font-semibold">Revenue by settlement</h2>
          <BiChart
            type="bar"
            labels={rows.map((r) => r.name || "")}
            values={rows.map((r) => r.revenue)}
          />
        </div>
      </div>

      <div className="bi-card overflow-hidden">
        <div className="border-b border-slate-100 px-5 py-4 dark:border-slate-800">
          <h2 className="text-sm font-semibold">Payment channel contribution</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="bi-table">
            <thead>
              <tr>
                <th>Settlement</th>
                <th>Revenue</th>
                <th>Orders</th>
                <th>AOV</th>
                <th>Share</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.name || "x"}>
                  <td className="font-medium">{row.name}</td>
                  <td>{formatCurrency(row.revenue)}</td>
                  <td>{formatNumber(row.orders)}</td>
                  <td>{formatCurrency(row.aov || 0)}</td>
                  <td>
                    {totalRevenue
                      ? `${((row.revenue / totalRevenue) * 100).toFixed(1)}%`
                      : "—"}
                  </td>
                </tr>
              ))}
              {!loading && rows.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-10 text-center text-slate-500">
                    No settlement data for current filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="bi-card overflow-hidden">
        <div className="border-b border-slate-100 px-5 py-4 dark:border-slate-800">
          <h2 className="text-sm font-semibold">Outlet-wise settlement patterns</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="bi-table">
            <thead>
              <tr>
                <th>Outlet</th>
                <th>Settlement</th>
                <th>Revenue</th>
                <th>Orders</th>
              </tr>
            </thead>
            <tbody>
              {outletWise.map((row, idx) => (
                <tr key={`${row.outlet}-${row.settlement}-${idx}`}>
                  <td>{row.outlet}</td>
                  <td>{row.settlement}</td>
                  <td>{formatCurrency(row.revenue)}</td>
                  <td>{formatNumber(row.orders)}</td>
                </tr>
              ))}
              {!loading && outletWise.length === 0 && (
                <tr>
                  <td colSpan={4} className="py-10 text-center text-slate-500">
                    No outlet settlement rows.
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
