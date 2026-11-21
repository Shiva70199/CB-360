"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useAuth } from "./auth";
import {
  restaurantApi,
  type FilterOptions,
  type RestaurantFilters,
} from "./restaurant";

interface FilterContextValue {
  filters: RestaurantFilters;
  options: FilterOptions | null;
  loadingOptions: boolean;
  setFilter: <K extends keyof RestaurantFilters>(key: K, value: RestaurantFilters[K]) => void;
  setFilters: (next: RestaurantFilters) => void;
  clearAll: () => void;
  refreshOptions: () => Promise<void>;
}

const FilterContext = createContext<FilterContextValue | null>(null);
const STORAGE_KEY = "databoard_restaurant_filters";

const EMPTY: RestaurantFilters = {
  date_from: "",
  date_to: "",
  brand: "",
  outlet: "",
  menu_group: "",
  order_type: "",
  settlement: "",
};

export function FilterProvider({ children }: { children: ReactNode }) {
  const { token } = useAuth();
  const [filters, setFiltersState] = useState<RestaurantFilters>(EMPTY);
  const [options, setOptions] = useState<FilterOptions | null>(null);
  const [loadingOptions, setLoadingOptions] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as RestaurantFilters;
        setFiltersState({ ...EMPTY, ...parsed });
      }
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(filters));
  }, [filters]);

  const refreshOptions = useCallback(async () => {
    if (!token) return;
    setLoadingOptions(true);
    try {
      const res = await restaurantApi.filters(token);
      setOptions(res.data);
    } catch {
      setOptions(null);
    } finally {
      setLoadingOptions(false);
    }
  }, [token]);

  useEffect(() => {
    refreshOptions();
  }, [refreshOptions]);

  const setFilter = useCallback(<K extends keyof RestaurantFilters>(key: K, value: RestaurantFilters[K]) => {
    setFiltersState((prev) => ({ ...prev, [key]: value }));
  }, []);

  const setFilters = useCallback((next: RestaurantFilters) => {
    setFiltersState({ ...EMPTY, ...next });
  }, []);

  const clearAll = useCallback(() => {
    setFiltersState(EMPTY);
  }, []);

  const value = useMemo(
    () => ({
      filters,
      options,
      loadingOptions,
      setFilter,
      setFilters,
      clearAll,
      refreshOptions,
    }),
    [filters, options, loadingOptions, setFilter, setFilters, clearAll, refreshOptions]
  );

  return <FilterContext.Provider value={value}>{children}</FilterContext.Provider>;
}

export function useRestaurantFilters() {
  const ctx = useContext(FilterContext);
  if (!ctx) throw new Error("useRestaurantFilters must be used within FilterProvider");
  return ctx;
}

/** Strip empty strings so API query stays clean. */
export function activeFilters(filters: RestaurantFilters): RestaurantFilters {
  const out: RestaurantFilters = {};
  (Object.keys(filters) as (keyof RestaurantFilters)[]).forEach((key) => {
    const v = filters[key];
    if (v) out[key] = v;
  });
  return out;
}
