const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

import { ApiError } from "./api";

export interface RestaurantFilters {
  date_from?: string;
  date_to?: string;
  brand?: string;
  outlet?: string;
  menu_group?: string;
  order_type?: string;
  settlement?: string;
}

export interface RestaurantMeta {
  query_ms?: number;
}

export interface RestaurantResponse<T> {
  data: T;
  meta?: RestaurantMeta;
}

export interface KpiData {
  total_revenue: number;
  total_orders: number;
  aov: number;
  total_items_sold: number;
  total_transactions: number;
  active_outlets: number;
  comparison: {
    previous: {
      total_revenue: number;
      total_orders: number;
      aov: number;
      total_items_sold: number;
      total_transactions: number;
      active_outlets: number;
    };
    growth: {
      total_revenue_pct: number | null;
      total_orders_pct: number | null;
      aov_pct: number | null;
    };
  } | null;
}

export interface TrendPoint {
  period: string | null;
  revenue: number;
  orders: number;
}

export interface NamedRevenueRow {
  name: string | null;
  revenue: number;
  orders: number;
  aov?: number;
  items_sold?: number;
}

export interface ProductRow {
  item: string | null;
  menu_group: string | null;
  revenue: number;
  quantity: number;
  avg_price?: number | null;
  contribution_pct?: number | null;
}

export interface PaginatedProducts {
  items: ProductRow[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface TransactionRow {
  id: number;
  bill_no: string;
  outlet_name: string;
  brand: string;
  order_datetime: string | null;
  menu_group: string;
  item: string;
  price: number;
  quantity: number;
  line_revenue: number;
  order_type: string;
  settlement: string;
  order_key: string;
}

export interface PaginatedTransactions {
  items: TransactionRow[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface FilterOptions {
  brands: string[];
  outlets: string[];
  menu_groups: string[];
  order_types: string[];
  settlements: string[];
  date_min: string | null;
  date_max: string | null;
}

export interface ImportBatch {
  id: number;
  filename: string;
  file_hash: string;
  imported_at: string | null;
  status: string;
  total_rows: number;
  valid_rows: number;
  rejected_rows: number;
  missing_values?: Record<string, number>;
  error_report_path?: string | null;
  source_path?: string | null;
  notes?: string | null;
}

export interface InsightItem {
  title: string;
  detail: string;
}

export interface OrderTypeAnalytics {
  distribution: NamedRevenueRow[];
  outlet_wise: {
    outlet: string | null;
    order_type: string | null;
    revenue: number;
    orders: number;
  }[];
}

function buildQuery(
  filters: RestaurantFilters = {},
  extra: Record<string, string | number | boolean | undefined> = {}
): string {
  const params = new URLSearchParams();
  Object.entries({ ...filters, ...extra }).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    params.set(key, String(value));
  });
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

async function restaurantRequest<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null
): Promise<RestaurantResponse<T>> {
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!(options.body instanceof FormData) && !headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join(", ")
          : data.error || "Request failed.";
    throw new ApiError(message, res.status);
  }
  return data as RestaurantResponse<T>;
}

export const restaurantApi = {
  kpis: (token: string, filters: RestaurantFilters = {}) =>
    restaurantRequest<KpiData>(`/restaurant/kpis${buildQuery(filters)}`, {}, token),

  trends: (token: string, filters: RestaurantFilters = {}, granularity: "day" | "week" | "month" = "day") =>
    restaurantRequest<TrendPoint[]>(
      `/restaurant/trends${buildQuery(filters, { granularity })}`,
      {},
      token
    ),

  outlets: (token: string, filters: RestaurantFilters = {}) =>
    restaurantRequest<NamedRevenueRow[]>(`/restaurant/outlets${buildQuery(filters)}`, {}, token),

  brands: (token: string, filters: RestaurantFilters = {}) =>
    restaurantRequest<NamedRevenueRow[]>(`/restaurant/brands${buildQuery(filters)}`, {}, token),

  categories: (token: string, filters: RestaurantFilters = {}) =>
    restaurantRequest<NamedRevenueRow[]>(`/restaurant/categories${buildQuery(filters)}`, {}, token),

  products: (
    token: string,
    filters: RestaurantFilters = {},
    opts: { search?: string; sort?: string; page?: number; page_size?: number } = {}
  ) =>
    restaurantRequest<PaginatedProducts>(
      `/restaurant/products${buildQuery(filters, opts)}`,
      {},
      token
    ),

  productContribution: (token: string, filters: RestaurantFilters = {}, limit = 10) =>
    restaurantRequest<{ top_items: ProductRow[]; contribution: ProductRow[] }>(
      `/restaurant/products${buildQuery(filters, { contribution: true, limit })}`,
      {},
      token
    ),

  orderTypes: (token: string, filters: RestaurantFilters = {}) =>
    restaurantRequest<OrderTypeAnalytics>(`/restaurant/order-types${buildQuery(filters)}`, {}, token),

  settlements: (token: string, filters: RestaurantFilters = {}) =>
    restaurantRequest<{
      distribution: NamedRevenueRow[];
      outlet_wise: { outlet: string | null; settlement: string | null; revenue: number; orders: number }[];
    }>(`/restaurant/settlements${buildQuery(filters)}`, {}, token),

  transactions: (
    token: string,
    filters: RestaurantFilters = {},
    page = 1,
    page_size = 50
  ) =>
    restaurantRequest<PaginatedTransactions>(
      `/restaurant/transactions${buildQuery(filters, { page, page_size })}`,
      {},
      token
    ),

  filters: (token: string) =>
    restaurantRequest<FilterOptions>("/restaurant/filters", {}, token),

  insights: (token: string, filters: RestaurantFilters = {}) =>
    restaurantRequest<InsightItem[]>(`/restaurant/insights${buildQuery(filters)}`, {}, token),

  imports: (token: string) =>
    restaurantRequest<ImportBatch[]>("/restaurant/imports", {}, token),

  importFromPath: (token: string, path?: string, force = false) =>
    restaurantRequest<ImportBatch>("/restaurant/imports/from-path", {
      method: "POST",
      body: JSON.stringify({ path: path || null, force }),
    }, token),

  importUpload: async (token: string, file: File, force = false) => {
    const form = new FormData();
    form.append("file", file);
    return restaurantRequest<ImportBatch>(
      `/restaurant/imports/upload?force=${force}`,
      { method: "POST", body: form },
      token
    );
  },

  exportCsv: async (token: string, filters: RestaurantFilters = {}) => {
    const res = await fetch(`${API_BASE}/restaurant/export.csv${buildQuery(filters)}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      throw new ApiError("Export failed.", res.status);
    }
    return res.blob();
  },
};

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value || 0);
}

export function formatNumber(value: number, digits = 0): string {
  return new Intl.NumberFormat("en-IN", {
    maximumFractionDigits: digits,
  }).format(value || 0);
}
