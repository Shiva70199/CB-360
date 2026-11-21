"use client";

import { useEffect, useRef } from "react";
import { EmptyState } from "./EmptyState";

export type BiChartType = "line" | "area" | "bar" | "donut" | "pie";

interface BiChartProps {
  type: BiChartType;
  labels: string[];
  values: number[];
  seriesName?: string;
  height?: number;
  currency?: boolean;
}

function formatValue(n: number, currency?: boolean) {
  if (currency) {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(n);
  }
  return new Intl.NumberFormat("en-IN").format(n);
}

export function BiChart({
  type,
  labels,
  values,
  seriesName = "Revenue",
  height = 300,
  currency = true,
}: BiChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<{
    setOption: (o: unknown, n?: boolean) => void;
    resize: () => void;
    dispose: () => void;
  } | null>(null);

  const hasData = labels.length > 0 && values.some((v) => v !== 0 || values.length > 0) && values.length > 0;

  useEffect(() => {
    if (!containerRef.current || !hasData) return;
    let cancelled = false;

    async function render() {
      const echarts = await import("echarts");
      if (cancelled || !containerRef.current) return;
      if (!chartRef.current) {
        chartRef.current = echarts.init(containerRef.current);
      }

      const palette = ["#14532d", "#059669", "#34d399", "#0f766e", "#1f2937", "#6ee7b7", "#166534"];

      let option: Record<string, unknown>;
      if (type === "donut" || type === "pie") {
        option = {
          tooltip: {
            trigger: "item",
            formatter: (p: { name: string; value: number; percent: number }) =>
              `${p.name}<br/>${formatValue(p.value, currency)} (${p.percent}%)`,
          },
          legend: { bottom: 0, type: "scroll", textStyle: { color: "#64748b" } },
          series: [
            {
              type: "pie",
              radius: type === "donut" ? ["48%", "72%"] : ["0%", "70%"],
              center: ["50%", "46%"],
              data: labels.map((name, i) => ({ name, value: values[i] ?? 0 })),
              itemStyle: { borderRadius: 6, borderColor: "#fff", borderWidth: 2 },
              color: palette,
              label: { color: "#475569" },
            },
          ],
        };
      } else {
        option = {
          color: ["#14532d"],
          grid: { left: 52, right: 20, top: 28, bottom: 40 },
          tooltip: {
            trigger: "axis",
            valueFormatter: (v: number) => formatValue(Number(v), currency),
          },
          xAxis: {
            type: "category",
            data: labels,
            axisLabel: { color: "#64748b", hideOverlap: true },
            axisLine: { lineStyle: { color: "#e2e8f0" } },
          },
          yAxis: {
            type: "value",
            axisLabel: {
              color: "#64748b",
              formatter: (v: number) =>
                currency
                  ? new Intl.NumberFormat("en-IN", { notation: "compact" }).format(v)
                  : String(v),
            },
            splitLine: { lineStyle: { color: "rgba(148,163,184,0.25)" } },
          },
          series: [
            {
              name: seriesName,
              type: type === "area" ? "line" : type,
              data: values,
              smooth: type === "line" || type === "area",
              areaStyle: type === "area" ? { color: "rgba(20,83,45,0.14)" } : undefined,
              itemStyle: {
                color: "#14532d",
                borderRadius: type === "bar" ? [4, 4, 0, 0] : undefined,
              },
              lineStyle: { width: 2.5 },
              symbolSize: 6,
            },
          ],
        };
      }

      chartRef.current.setOption(option, true);
      chartRef.current.resize();
    }

    render();
    const onResize = () => chartRef.current?.resize();
    window.addEventListener("resize", onResize);
    return () => {
      cancelled = true;
      window.removeEventListener("resize", onResize);
    };
  }, [type, labels, values, seriesName, currency, hasData]);

  useEffect(() => {
    return () => {
      chartRef.current?.dispose();
      chartRef.current = null;
    };
  }, []);

  if (!hasData) {
    return <EmptyState title="Nothing to chart" detail="No aggregated values for the current filters." />;
  }

  return <div ref={containerRef} style={{ height }} className="w-full" />;
}
