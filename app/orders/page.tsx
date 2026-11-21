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
  type OrderTypeAnalytics,
} from "@/lib/restaurant";

export default function OrdersPage() {
  const { token, logout } = useAuth();
  const { filters } = useRestaurantFilters();
  const [data, setData] = useState<OrderTypeAnalytics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await restaurantApi.orderTypes(token, activeFilters(filters));
      setData(res.data);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        logout();
        return;
      }
      setError(err instanceof ApiError ? err.message : "Failed to load order analytics.");
    } finally {
      setLoading(false);
    }
  }, [token, filters, logout]);

  useEffect(() => {
    load();
  }, [load]);

  const dist = data?.distribution || [];

  return (
    <DashboardFrame
      title="Order Analytics"
      subtitle="Order types from imported transactions, including dine-in, takeaway and delivery"
    >
      {error && <ErrorState message={error} onRetry={load} />}

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="bi-card p-5">
          <h2 className="mb-3 text-sm font-semibold">Order distribution</h2>
          <BiChart
            type="donut"
            labels={dist.map((r) => r.name || "")}
            values={dist.map((r) => r.orders)}
            currency={false}
            seriesName="Orders"
          />
        </div>
        <div className="bi-card p-5">
          <h2 className="mb-3 text-sm font-semibold">Revenue by order type</h2>
          <BiChart
            type="bar"
            labels={dist.map((r) => r.name || "")}
            values={dist.map((r) => r.revenue)}
          />
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {dist.map((row) => (
          <div key={row.name || "unknown"} className="bi-card p-5">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              {row.name}
            </p>
            <p className="mt-2 text-xl font-bold">{formatCurrency(row.revenue)}</p>
            <p className="mt-1 text-sm text-slate-500">
              {formatNumber(row.orders)} orders · AOV {formatCurrency(row.aov || 0)}
            </p>
          </div>
        ))}
        {!loading && dist.length === 0 && (
          <div className="bi-card p-5 text-sm text-slate-500 sm:col-span-3">
            No order-type data for current filters.
          </div>
        )}
      </div>

      <div className="bi-card overflow-hidden">
        <div className="border-b border-slate-100 px-5 py-4 dark:border-slate-800">
          <h2 className="text-sm font-semibold">Outlet-wise order performance</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="bi-table">
            <thead>
              <tr>
                <th>Outlet</th>
                <th>Order type</th>
                <th>Revenue</th>
                <th>Orders</th>
              </tr>
            </thead>
            <tbody>
              {(data?.outlet_wise || []).map((row, idx) => (
                <tr key={`${row.outlet}-${row.order_type}-${idx}`}>
                  <td>{row.outlet}</td>
                  <td>{row.order_type}</td>
                  <td>{formatCurrency(row.revenue)}</td>
                  <td>{formatNumber(row.orders)}</td>
                </tr>
              ))}
              {!loading && (data?.outlet_wise?.length ?? 0) === 0 && (
                <tr>
                  <td colSpan={4} className="py-10 text-center text-slate-500">
                    No outlet-wise order rows.
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
