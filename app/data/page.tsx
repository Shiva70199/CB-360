"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { DashboardFrame } from "@/components/bi/DashboardFrame";
import { ErrorState } from "@/components/bi/ErrorState";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { activeFilters, useRestaurantFilters } from "@/lib/filters";
import { useToast } from "@/components/Toast";
import {
  formatNumber,
  restaurantApi,
  type ImportBatch,
  type PaginatedTransactions,
} from "@/lib/restaurant";

export default function DataManagementPage() {
  const { token, logout } = useAuth();
  const { filters, refreshOptions } = useRestaurantFilters();
  const { showToast } = useToast();
  const fileRef = useRef<HTMLInputElement>(null);
  const [imports, setImports] = useState<ImportBatch[]>([]);
  const [txns, setTxns] = useState<PaginatedTransactions | null>(null);
  const [page, setPage] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const [imp, txn] = await Promise.all([
        restaurantApi.imports(token),
        restaurantApi.transactions(token, activeFilters(filters), page, 25),
      ]);
      setImports(imp.data);
      setTxns(txn.data);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        logout();
        return;
      }
      setError(err instanceof ApiError ? err.message : "Failed to load data management.");
    } finally {
      setLoading(false);
    }
  }, [token, filters, page, logout]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleUpload(file: File) {
    if (!token) return;
    setBusy(true);
    try {
      const res = await restaurantApi.importUpload(token, file, false);
      showToast(
        `Imported ${res.data.valid_rows} valid / ${res.data.rejected_rows} rejected rows.`,
        "success"
      );
      await refreshOptions();
      await load();
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : "Upload failed.", "error");
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function importDefaultPath() {
    if (!token) return;
    setBusy(true);
    try {
      const res = await restaurantApi.importFromPath(token, undefined, false);
      showToast(
        `Import ${res.data.status}: ${res.data.valid_rows} valid rows from ${res.data.filename}.`,
        "success"
      );
      await refreshOptions();
      await load();
    } catch (err) {
      showToast(
        err instanceof ApiError
          ? err.message
          : "Default path import failed. Place restaurant_transactions.xlsx under data/source/.",
        "error"
      );
    } finally {
      setBusy(false);
    }
  }

  async function exportCsv() {
    if (!token) return;
    setBusy(true);
    try {
      const blob = await restaurantApi.exportCsv(token, activeFilters(filters));
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "restaurant_export.csv";
      a.click();
      URL.revokeObjectURL(url);
      showToast("Export downloaded.", "success");
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : "Export failed.", "error");
    } finally {
      setBusy(false);
    }
  }

  const latest = imports[0];

  return (
    <DashboardFrame
      title="Data Management"
      subtitle="Import California Burrito transactions, review batches and export filtered CSV"
    >
      {error && <ErrorState message={error} onRetry={load} />}

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="bi-card space-y-3 p-5 lg:col-span-2">
          <h2 className="text-sm font-semibold">Import restaurant dataset</h2>
          <p className="text-sm text-slate-500">
            Upload `.xlsx` / `.csv` or import from{" "}
            <code className="rounded bg-slate-100 px-1 text-xs dark:bg-slate-800">
              data/source/restaurant_transactions.xlsx
            </code>
            . Duplicate file hashes are skipped.
          </p>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              className="bi-btn-primary"
              disabled={busy}
              onClick={() => fileRef.current?.click()}
            >
              Upload file
            </button>
            <input
              ref={fileRef}
              type="file"
              accept=".xlsx,.xls,.csv"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleUpload(file);
              }}
            />
            <button
              type="button"
              className="bi-btn-secondary"
              disabled={busy}
              onClick={importDefaultPath}
            >
              Import default path
            </button>
            <button type="button" className="bi-btn-secondary" disabled={busy} onClick={exportCsv}>
              Export filtered CSV
            </button>
            <Link href="/datasets" className="bi-btn-secondary">
              Legacy CSV datasets
            </Link>
          </div>
        </div>

        <div className="bi-card p-5">
          <h2 className="text-sm font-semibold">Latest import</h2>
          {latest ? (
            <dl className="mt-3 space-y-2 text-sm">
              <div className="flex justify-between gap-2">
                <dt className="text-slate-500">File</dt>
                <dd className="truncate font-medium">{latest.filename}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-slate-500">Status</dt>
                <dd className="font-medium capitalize">{latest.status}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-slate-500">Processed</dt>
                <dd>{formatNumber(latest.total_rows)}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-slate-500">Valid</dt>
                <dd>{formatNumber(latest.valid_rows)}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-slate-500">Rejected</dt>
                <dd>{formatNumber(latest.rejected_rows)}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-slate-500">Imported</dt>
                <dd>{latest.imported_at ? latest.imported_at.slice(0, 19).replace("T", " ") : "—"}</dd>
              </div>
            </dl>
          ) : (
            <p className="mt-3 text-sm text-slate-500">No imports yet.</p>
          )}
        </div>
      </div>

      <div className="bi-card overflow-hidden">
        <div className="border-b border-slate-100 px-5 py-4 dark:border-slate-800">
          <h2 className="text-sm font-semibold">Import history</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="bi-table">
            <thead>
              <tr>
                <th>File</th>
                <th>Date</th>
                <th>Status</th>
                <th>Total</th>
                <th>Valid</th>
                <th>Rejected</th>
                <th>Missing values</th>
              </tr>
            </thead>
            <tbody>
              {imports.map((batch) => (
                <tr key={batch.id}>
                  <td className="font-medium">{batch.filename}</td>
                  <td>{batch.imported_at ? batch.imported_at.slice(0, 19).replace("T", " ") : "—"}</td>
                  <td className="capitalize">{batch.status}</td>
                  <td>{formatNumber(batch.total_rows)}</td>
                  <td>{formatNumber(batch.valid_rows)}</td>
                  <td>{formatNumber(batch.rejected_rows)}</td>
                  <td className="max-w-[220px] truncate text-xs text-slate-500">
                    {batch.missing_values
                      ? Object.entries(batch.missing_values)
                          .filter(([, v]) => v > 0)
                          .map(([k, v]) => `${k}:${v}`)
                          .join(", ") || "—"
                      : "—"}
                  </td>
                </tr>
              ))}
              {!loading && imports.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-10 text-center text-slate-500">
                    No import batches recorded.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="bi-card overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4 dark:border-slate-800">
          <h2 className="text-sm font-semibold">Paginated transactions</h2>
          <span className="text-xs text-slate-500">
            {txns ? `${formatNumber(txns.total)} rows` : ""}
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="bi-table">
            <thead>
              <tr>
                <th>Bill</th>
                <th>Outlet</th>
                <th>Item</th>
                <th>Qty</th>
                <th>Revenue</th>
                <th>Type</th>
                <th>Settlement</th>
                <th>When</th>
              </tr>
            </thead>
            <tbody>
              {(txns?.items || []).map((row) => (
                <tr key={row.id}>
                  <td>{row.bill_no}</td>
                  <td>{row.outlet_name}</td>
                  <td>{row.item}</td>
                  <td>{row.quantity}</td>
                  <td>{row.line_revenue}</td>
                  <td>{row.order_type}</td>
                  <td>{row.settlement}</td>
                  <td className="whitespace-nowrap text-xs">
                    {row.order_datetime ? row.order_datetime.slice(0, 19).replace("T", " ") : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-100 px-5 py-3 dark:border-slate-800">
          <button
            type="button"
            className="bi-btn-secondary"
            disabled={!txns || page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Previous
          </button>
          <span className="px-2 py-1 text-sm text-slate-600">
            {txns?.page ?? 1} / {txns?.total_pages ?? 1}
          </span>
          <button
            type="button"
            className="bi-btn-secondary"
            disabled={!txns || page >= (txns.total_pages || 1)}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </button>
        </div>
      </div>
    </DashboardFrame>
  );
}
