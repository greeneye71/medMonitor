/* medMonitor UI: history chart, pairing countdown, confirmations, preset thresholds. */
(function () {
  "use strict";

  const fmt = (v) => (v == null ? "—" : v.toFixed(1).replace(".", ",").replace("-", "−"));
  const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

  // History chart -------------------------------------------------------------
  function initChart() {
    const el = document.getElementById("chart");
    const data = document.getElementById("chart-data");
    if (!el || !data || !window.echarts) return;
    const d = JSON.parse(data.textContent);
    const ink = css("--ink") || "#1b2a33";
    const muted = css("--muted") || "#5f6f78";
    const line = css("--line") || "#d5dde1";
    const ok = css("--ok") || "#1D9E75";
    const alarm = css("--alarm") || "#E24B4A";
    const hasBand = d.min != null && d.max != null;

    const chart = echarts.init(el, null, { renderer: "canvas" });
    chart.setOption({
      animation: false,
      grid: { left: 48, right: 16, top: 16, bottom: 36 },
      tooltip: {
        trigger: "axis",
        valueFormatter: (v) => fmt(v) + " °C",
      },
      xAxis: {
        type: "time", min: d.start, max: d.end,
        axisLine: { lineStyle: { color: line } },
        axisLabel: { color: muted, hideOverlap: true },
        splitLine: { show: false },
      },
      yAxis: {
        type: "value", scale: true,
        axisLabel: { color: muted, formatter: (v) => fmt(v) },
        splitLine: { lineStyle: { color: line, type: "dashed" } },
      },
      visualMap: hasBand ? {
        show: false, dimension: 1,
        pieces: [{ lt: d.min, color: alarm }, { gte: d.min, lte: d.max, color: ok }, { gt: d.max, color: alarm }],
      } : undefined,
      series: [{
        type: "line", data: d.points, showSymbol: false, connectNulls: false,
        lineStyle: { width: 2 }, itemStyle: { color: ink },
        markArea: hasBand ? {
          silent: true, itemStyle: { color: ok, opacity: 0.08 },
          data: [[{ yAxis: d.min }, { yAxis: d.max }]],
        } : undefined,
        markLine: hasBand ? {
          silent: true, symbol: "none",
          lineStyle: { color: ok, type: "dashed", opacity: 0.6 },
          label: { color: muted, formatter: (p) => fmt(p.value) },
          data: [{ yAxis: d.min }, { yAxis: d.max }],
        } : undefined,
      }],
    });
    // Keep the threshold band visible even when all readings sit inside it.
    if (hasBand) {
      const ys = d.points.map((p) => p[1]).filter((v) => v != null);
      chart.setOption({ yAxis: {
        min: Math.floor(Math.min(d.min, ...ys) - 1),
        max: Math.ceil(Math.max(d.max, ...ys) + 1),
      } });
    }
    window.addEventListener("resize", () => chart.resize());
  }

  // Pairing countdown -----------------------------------------------------------
  let timer = null;
  function initCountdown() {
    if (timer) clearInterval(timer);
    const el = document.querySelector(".countdown[data-seconds]");
    if (!el) return;
    let left = parseInt(el.dataset.seconds, 10) || 0;
    timer = setInterval(() => {
      left = Math.max(0, left - 1);
      el.textContent = left;
      if (left === 0) {
        clearInterval(timer);
        const box = document.getElementById("discovered");
        if (box && window.htmx) htmx.ajax("GET", "/impostazioni/sensori/rilevati", { target: box, swap: "outerHTML" });
      }
    }, 1000);
  }

  // Confirm before destructive submits ------------------------------------------
  document.addEventListener("submit", (e) => {
    const msg = e.target.dataset && e.target.dataset.confirm;
    if (msg && !window.confirm(msg)) e.preventDefault();
  }, true);

  // Kind select fills preset thresholds ----------------------------------------
  document.addEventListener("change", (e) => {
    const sel = e.target;
    if (!sel.matches || !sel.matches("select[data-preset-target]")) return;
    const opt = sel.selectedOptions[0];
    const form = sel.closest("form");
    if (!opt || !form) return;
    const min = form.querySelector('[data-role="min"]');
    const max = form.querySelector('[data-role="max"]');
    if (min) min.value = opt.dataset.min;
    if (max) max.value = opt.dataset.max;
  });

  // Auto-submit filters (history sensor select, events filters) -----------------
  document.addEventListener("change", (e) => {
    if (e.target.matches && e.target.matches("[data-autosubmit]")) e.target.form.requestSubmit();
  });

  document.addEventListener("DOMContentLoaded", () => { initChart(); initCountdown(); });
  document.addEventListener("htmx:afterSwap", initCountdown);
})();
