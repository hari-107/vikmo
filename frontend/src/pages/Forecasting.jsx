import { useTheme } from "../components/theme-context";
import React, { useState, useEffect, useCallback } from "react";
import {
  TrendingUp,
  Search,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { getReorderSuggestions, getForecast } from "../services/api";
import { StockBadge } from "../components/Badge";
import { TableSkeleton } from "../components/LoadingSkeleton";
import { EmptyState } from "../components/EmptyState";

function formatWeek(dateString) {
  const date = new Date(`${dateString}T00:00:00`);
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}

export function Forecasting() {
  const { reducedMotion } = useTheme();
  const [reorders, setReorders] = useState([]);
  const [loadingReorders, setLoadingReorders] = useState(true);
  const [reordersError, setReordersError] = useState(null);

  // The selected SKU's forecast contains four future weekly predictions.
  const [selectedSku, setSelectedSku] = useState("");
  const [forecastData, setForecastData] = useState([]);
  const [loadingForecast, setLoadingForecast] = useState(false);
  const [forecastError, setForecastError] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");

  const fetchReorders = useCallback(async () => {
    setLoadingReorders(true);
    setReordersError(null);
    try {
      const res = await getReorderSuggestions();
      const list = res.results || [];
      setReorders(list);
      if (list.length > 0) {
        const topUrgent = list.find((x) => x.reorder_qty > 0) || list[0];
        setSelectedSku((previous) => previous || topUrgent.sku);
      }
    } catch (err) {
      setReordersError(err.message || "Failed to load reorder recommendations.");
    } finally {
      setLoadingReorders(false);
    }
  }, []);

  const fetchSkuForecast = useCallback(async (sku) => {
    setLoadingForecast(true);
    setForecastError(null);
    try {
      const res = await getForecast(sku);
      const points = (res.forecast || []).slice().sort(
        (a, b) => a.week_start.localeCompare(b.week_start)
      );
      setForecastData(points);
    } catch (err) {
      setForecastError(err.message || `Failed to load forecast for ${sku}.`);
    } finally {
      setLoadingForecast(false);
    }
  }, []);

  const selectedMetrics = reorders.find((r) => r.sku === selectedSku);
  const filteredReorders = reorders.filter((r) =>
    r.sku.toLowerCase().includes(searchTerm.toLowerCase().trim())
  );
  const forecastRange = forecastData.length
    ? `${formatWeek(forecastData[0].week_start)} – ${formatWeek(forecastData[forecastData.length - 1].week_start)}`
    : "";

  useEffect(() => {
    // Loading state tracks this external API request.
    // oxlint-disable-next-line react/set-state-in-effect
    fetchReorders();
  }, [fetchReorders]);

  useEffect(() => {
    if (selectedSku) {
      // Loading state tracks the selected SKU request.
      // oxlint-disable-next-line react/set-state-in-effect
      fetchSkuForecast(selectedSku);
    }
  }, [selectedSku, fetchSkuForecast]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-bold tracking-tight text-foreground">
            Demand Forecasting & Reorder Analytics
          </h1>
          <p className="text-sm text-secondary">
            Predict demand for the next four weeks using sales history, promotions, and seasonal patterns.
          </p>
        </div>
        <div className="inline-flex items-center gap-2 self-start rounded-full border border-line bg-surface px-3 py-2 text-xs font-semibold text-foreground">
          <span className="h-2 w-2 rounded-full bg-success" />
          Upcoming 4 weeks
        </div>
      </div>

      <div className="panel rounded-xl border border-line shadow-xs p-6 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-line/60 pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-primary-soft rounded-lg text-primary shadow-2xs">
              <TrendingUp className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-display font-bold text-lg text-foreground">
                4-Week Demand Forecast: {selectedSku}
              </h2>
              <p className="text-xs text-secondary">
                {forecastRange ? `Forecast weeks: ${forecastRange}` : "Weekly predicted demand for the selected part."}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-secondary">Switch SKU:</span>
            <select
              value={selectedSku}
              onChange={(e) => setSelectedSku(e.target.value)}
              className="text-xs font-mono font-bold bg-surface border border-line rounded-xl px-3 py-1.5 text-foreground focus:outline-none focus:ring-2 focus:ring-primary cursor-pointer"
            >
              {reorders.map((r) => (
                <option key={r.sku} value={r.sku}>
                  {r.sku} {r.reorder_qty > 0 ? `(Reorder: +${r.reorder_qty})` : ""}
                </option>
              ))}
            </select>
          </div>
        </div>

        {selectedMetrics && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="p-4 bg-surface rounded-lg border border-line shadow-2xs">
              <div className="text-[11px] font-semibold text-secondary uppercase tracking-wider">
                Live Stock
              </div>
              <div className="text-xl font-bold text-foreground font-display mt-1">
                {selectedMetrics.current_stock} units
              </div>
              <div className="text-[11px] text-secondary">Available warehouse inventory</div>
            </div>

            <div className="p-4 bg-surface rounded-lg border border-line shadow-2xs">
              <div className="text-[11px] font-semibold text-secondary uppercase tracking-wider">
                Supplier Lead Time
              </div>
              <div className="text-xl font-bold text-foreground font-display mt-1">
                {selectedMetrics.lead_time_weeks} {selectedMetrics.lead_time_weeks === 1 ? "week" : "weeks"}
              </div>
              <div className="text-[11px] text-secondary">Restock lead delay (L)</div>
            </div>

            <div className="p-4 bg-surface rounded-lg border border-line shadow-2xs">
              <div className="text-[11px] font-semibold text-secondary uppercase tracking-wider">
                Lead Time Demand
              </div>
              <div className="text-xl font-bold text-foreground font-display mt-1 font-mono">
                {selectedMetrics.lead_time_demand}
              </div>
              <div className="text-[11px] text-secondary">Forecast units across L weeks</div>
            </div>

            <div className="p-4 bg-surface rounded-lg border border-line shadow-2xs">
              <div className="text-[11px] font-semibold text-secondary uppercase tracking-wider">
                Safety Stock Buffer
              </div>
              <div className="text-xl font-bold text-foreground font-display mt-1 font-mono">
                {selectedMetrics.safety_stock}
              </div>
              <div className="text-[11px] text-secondary">ceil(1.65 × σ × √L)</div>
            </div>

            <div className={`p-4 rounded-lg border shadow-2xs ${
              selectedMetrics.reorder_qty > 0
                ? "bg-primary-soft/70 border-primary/40 text-primary-hover"
                : "bg-success-soft border-success-line text-success-ink"
            }`}>
              <div className="text-[11px] font-semibold uppercase tracking-wider">
                Suggested Reorder Qty
              </div>
              <div className="text-xl font-bold mt-1 font-display">
                {selectedMetrics.reorder_qty > 0 ? `+${selectedMetrics.reorder_qty} units` : "0 (Adequate)"}
              </div>
              <div className="text-[11px] opacity-80">
                Reorder point: {selectedMetrics.reorder_point}
              </div>
            </div>
          </div>
        )}

        <div className="h-64 w-full pt-2">
          {loadingForecast ? (
            <div role="status" className="h-full animate-pulse rounded-lg bg-subtle flex items-center justify-center text-xs text-secondary">
              Loading upcoming forecast…
            </div>
          ) : forecastError ? (
            <div className="h-full flex items-center justify-center text-xs text-danger">
              {forecastError}
            </div>
          ) : forecastData.length === 0 ? (
            <div className="h-full flex items-center justify-center text-xs text-secondary">
              No upcoming weekly forecast points available.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={forecastData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--line)" />
                <XAxis
                  dataKey="week_start"
                  tickFormatter={formatWeek}
                  tick={{ fontSize: 11, fill: "var(--secondary)" }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 11, fill: "var(--secondary)" }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  cursor={{ fill: "var(--subtle)" }}
                  itemStyle={{ color: "var(--foreground)" }}
                  formatter={(val) => [`${val} units`, "Predicted Demand"]}
                  labelFormatter={(lbl) => `Week starting ${formatWeek(lbl)}`}
                  contentStyle={{
                    backgroundColor: "var(--surface)",
                    color: "var(--foreground)",
                    borderRadius: "12px",
                    fontSize: "12px",
                    border: "1px solid var(--line)",
                    boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
                  }}
                />
                <Bar
                  isAnimationActive={!reducedMotion}
                  dataKey="forecast_units"
                  fill="var(--primary)"
                  radius={[8, 8, 0, 0]}
                  name="Forecasted Units"
                />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="panel rounded-xl border border-line shadow-xs overflow-hidden space-y-0">
        <div className="p-5 border-b border-line flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="font-display font-bold text-base text-foreground">
              Forecast SKUs & Inventory Thresholds
            </h3>
            <p className="text-xs text-secondary">
              Reorder quantities are calculated from the forecast horizon and live warehouse inventory.
            </p>
          </div>
          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-secondary" />
            <input
              type="text"
              aria-label="Filter forecast SKUs"
              placeholder="Filter by SKU code..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs form-control bg-surface border border-line rounded-xl text-foreground placeholder-secondary focus:outline-none focus:ring-2 focus:ring-primary font-mono"
            />
          </div>
        </div>

        {loadingReorders ? (
          <div className="p-6">
            <TableSkeleton rows={8} cols={7} />
          </div>
        ) : reordersError ? (
          <div role="alert" className="p-6 text-center text-danger text-sm">
            {reordersError}
            <div className="mt-3"><button className="btn-secondary text-xs" onClick={fetchReorders}>Try again</button></div>
          </div>
        ) : filteredReorders.length === 0 ? (
          <EmptyState
            title="No matching forecast SKUs"
            description="Clear your search to view all forecast SKUs."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="data-table w-full text-left text-sm">
              <thead className="bg-subtle border-b border-line text-xs font-semibold text-secondary uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3.5">SKU Code</th>
                  <th className="px-5 py-3.5">Live Stock</th>
                  <th className="px-5 py-3.5">Lead Time (L)</th>
                  <th className="px-5 py-3.5">Lead Demand</th>
                  <th className="px-5 py-3.5">Safety Stock</th>
                  <th className="px-5 py-3.5">Reorder Point</th>
                  <th className="px-5 py-3.5 text-right">Reorder Qty</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line/60">
                {filteredReorders.map((r) => {
                  const isSelected = r.sku === selectedSku;
                  const isUrgent = r.reorder_qty > 0;
                  return (
                    <tr
                      key={r.sku}
                      onClick={() => setSelectedSku(r.sku)}
                      tabIndex={0}
                      aria-label={`View forecast for ${r.sku}`}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          setSelectedSku(r.sku);
                        }
                      }}
                      className={`cursor-pointer transition-colors ${
                        isSelected ? "bg-primary-soft/50" : "hover:bg-surface"
                      }`}
                    >
                      <td className="px-5 py-3 font-mono text-xs font-bold text-foreground">
                        {r.sku}
                        {isSelected && (
                          <span className="ml-2 px-2 py-0.5 rounded-full text-[10px] bg-primary text-on-primary font-bold">
                            Active
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-3">
                        <StockBadge stock={r.current_stock} />
                      </td>
                      <td className="px-5 py-3 text-xs text-secondary">
                        {r.lead_time_weeks} {r.lead_time_weeks === 1 ? "wk" : "wks"}
                      </td>
                      <td className="px-5 py-3 text-xs font-mono text-secondary">
                        {r.lead_time_demand}
                      </td>
                      <td className="px-5 py-3 text-xs font-mono text-secondary">
                        {r.safety_stock}
                      </td>
                      <td className="px-5 py-3 text-xs font-mono text-foreground font-semibold">
                        {r.reorder_point}
                      </td>
                      <td className="px-5 py-3 text-right font-mono font-bold">
                        {isUrgent ? (
                          <span className="text-primary-hover bg-primary-soft border border-line px-2.5 py-0.5 rounded-full text-xs">
                            +{r.reorder_qty} units
                          </span>
                        ) : (
                          <span className="text-secondary text-xs">0</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
