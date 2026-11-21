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
  type PaginatedProducts,
  type ProductRow,
} from "@/lib/restaurant";

export default function ProductsPage() {
  const { token, logout } = useAuth();
  const { filters } = useRestaurantFilters();
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("revenue");
  const [page, setPage] = useState(1);
  const [table, setTable] = useState<PaginatedProducts | null>(null);
  const [categories, setCategories] = useState<NamedRevenueRow[]>([]);
  const [lowest, setLowest] = useState<ProductRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    const f = activeFilters(filters);
    try {
      const [products, cats, asc] = await Promise.all([
        restaurantApi.products(token, f, { search, sort, page, page_size: 15 }),
        restaurantApi.categories(token, f),
        restaurantApi.products(token, f, { sort: "quantity_asc", page: 1, page_size: 8 }),
      ]);
      setTable(products.data);
      setCategories(cats.data);
      setLowest(asc.data.items || []);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        logout();
        return;
      }
      setError(err instanceof ApiError ? err.message : "Failed to load products.");
    } finally {
      setLoading(false);
    }
  }, [token, filters, search, sort, page, logout]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <DashboardFrame title="Menu Analytics" subtitle="Menu items, categories, contribution and mix">
      {error && <ErrorState message={error} onRetry={load} />}

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="bi-card p-5">
          <h2 className="mb-3 text-sm font-semibold">Category performance</h2>
          <BiChart
            type="donut"
            labels={categories.map((c) => c.name || "")}
            values={categories.map((c) => c.revenue)}
          />
        </div>
        <div className="bi-card p-5">
          <h2 className="mb-3 text-sm font-semibold">Lowest quantity sellers (sample)</h2>
          <BiChart
            type="bar"
            labels={lowest.map((r) => r.item || "")}
            values={lowest.map((r) => r.quantity)}
            currency={false}
            seriesName="Quantity"
          />
        </div>
      </div>

      <div className="bi-card overflow-hidden">
        <div className="flex flex-wrap items-center gap-3 border-b border-slate-100 px-5 py-4 dark:border-slate-800">
          <h2 className="mr-auto text-sm font-semibold">Product table</h2>
          <input
            className="bi-input w-48"
            placeholder="Search item or category"
            value={search}
            onChange={(e) => {
              setPage(1);
              setSearch(e.target.value);
            }}
          />
          <select
            className="bi-select"
            value={sort}
            onChange={(e) => {
              setPage(1);
              setSort(e.target.value);
            }}
          >
            <option value="revenue">Sort: revenue</option>
            <option value="quantity">Sort: quantity</option>
            <option value="avg_price">Sort: avg price</option>
            <option value="item">Sort: item</option>
          </select>
        </div>
        <div className="overflow-x-auto">
          <table className="bi-table">
            <thead>
              <tr>
                <th>Item</th>
                <th>Category</th>
                <th>Revenue</th>
                <th>Qty sold</th>
                <th>Avg price</th>
              </tr>
            </thead>
            <tbody>
              {(table?.items || []).map((row) => (
                <tr key={`${row.item}-${row.menu_group}`}>
                  <td className="font-medium text-slate-900 dark:text-slate-100">{row.item}</td>
                  <td>{row.menu_group}</td>
                  <td>{formatCurrency(row.revenue)}</td>
                  <td>{formatNumber(row.quantity)}</td>
                  <td>{formatCurrency(row.avg_price || 0)}</td>
                </tr>
              ))}
              {!loading && (table?.items?.length ?? 0) === 0 && (
                <tr>
                  <td colSpan={5} className="py-10 text-center text-slate-500">
                    No products match the current filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="flex items-center justify-between border-t border-slate-100 px-5 py-3 text-sm dark:border-slate-800">
          <span className="text-slate-500">
            {table ? `${table.total} products` : ""} {loading ? "· loading…" : ""}
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              className="bi-btn-secondary"
              disabled={!table || page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              Previous
            </button>
            <span className="px-2 py-1 text-slate-600 dark:text-slate-300">
              {table?.page ?? 1} / {table?.total_pages ?? 1}
            </span>
            <button
              type="button"
              className="bi-btn-secondary"
              disabled={!table || page >= (table.total_pages || 1)}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </DashboardFrame>
  );
}
