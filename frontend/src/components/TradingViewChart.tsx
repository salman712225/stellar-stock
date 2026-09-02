import React, { useEffect, useRef, useState } from "react";
import { createChart, CandlestickSeries, LineSeries, HistogramSeries, createSeriesMarkers } from "lightweight-charts";
import type { IChartApi, ISeriesApi, UTCTimestamp, SeriesMarker } from "lightweight-charts";

interface CandleData {
  datetime: string;
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ema_9?: number;
  ema_21?: number;
  ema_200?: number;
  supertrend?: number;
  range_filter?: number;
  range_buy?: boolean;
  range_sell?: boolean;
  bb_upper?: number;
  bb_lower?: number;
  vwap?: number;
}

interface TradingViewChartProps {
  candles: CandleData[];
  symbol: string;
}

export const TradingViewChart: React.FC<TradingViewChartProps> = ({ candles, symbol }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const volumeContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const volumeChartRef = useRef<IChartApi | null>(null);

  // Overlay visibility states
  const [showEMA9, setShowEMA9] = useState(true);
  const [showEMA21, setShowEMA21] = useState(true);
  const [showEMA200, setShowEMA200] = useState(false);
  const [showSupertrend, setShowSupertrend] = useState(true);
  const [showRangeFilter, setShowRangeFilter] = useState(true);
  const [showBB, setShowBB] = useState(false);
  const [showVWAP, setShowVWAP] = useState(false);

  // Series references
  const candSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const ema9SeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const ema21SeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const ema200SeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const stSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const rfSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const bbUpperRef = useRef<ISeriesApi<"Line"> | null>(null);
  const bbLowerRef = useRef<ISeriesApi<"Line"> | null>(null);
  const vwapRef = useRef<ISeriesApi<"Line"> | null>(null);
  const volSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);

  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current || !volumeContainerRef.current || candles.length === 0) return;

    // Reset containers
    chartContainerRef.current.innerHTML = "";
    volumeContainerRef.current.innerHTML = "";

    // 1. Price Chart
    const priceChart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 380,
      layout: {
        background: { color: "#131722" },
        textColor: "#d1d4dc",
        fontFamily: "Inter, sans-serif",
      },
      grid: {
        vertLines: { color: "#2a2e39" },
        horzLines: { color: "#2a2e39" },
      },
      timeScale: {
        borderColor: "#2a2e39",
        timeVisible: true,
        secondsVisible: false,
      },
    });
    chartRef.current = priceChart;

    // 2. Volume Chart
    const volumeChart = createChart(volumeContainerRef.current, {
      width: volumeContainerRef.current.clientWidth,
      height: 90,
      layout: {
        background: { color: "#131722" },
        textColor: "#d1d4dc",
        fontFamily: "Inter, sans-serif",
      },
      grid: {
        vertLines: { color: "#2a2e39" },
        horzLines: { color: "#2a2e39" },
      },
      timeScale: {
        visible: false,
        borderColor: "#2a2e39",
      },
    });
    volumeChartRef.current = volumeChart;

    // Synchronize time scales
    priceChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      if (range) volumeChart.timeScale().setVisibleLogicalRange(range);
    });
    volumeChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      if (range) priceChart.timeScale().setVisibleLogicalRange(range);
    });

    // 3. Add Series
    const candSeries = priceChart.addSeries(CandlestickSeries, {
      upColor: "#089981",
      downColor: "#f23645",
      borderVisible: false,
      wickUpColor: "#089981",
      wickDownColor: "#f23645",
    });
    candSeriesRef.current = candSeries;

    const ema9Series = priceChart.addSeries(LineSeries, { color: "#2196F3", lineWidth: 2, title: "EMA 9", visible: showEMA9 });
    ema9SeriesRef.current = ema9Series;

    const ema21Series = priceChart.addSeries(LineSeries, { color: "#FF9800", lineWidth: 2, title: "EMA 21", visible: showEMA21 });
    ema21SeriesRef.current = ema21Series;

    const ema200Series = priceChart.addSeries(LineSeries, { color: "#9C27B0", lineWidth: 2, title: "EMA 200", visible: showEMA200 });
    ema200SeriesRef.current = ema200Series;

    const stSeries = priceChart.addSeries(LineSeries, { color: "#E040FB", lineWidth: 2, lineStyle: 2, title: "Supertrend", visible: showSupertrend });
    stSeriesRef.current = stSeries;

    const rfSeries = priceChart.addSeries(LineSeries, { color: "#FFCA28", lineWidth: 2, title: "Range Filter", visible: showRangeFilter });
    rfSeriesRef.current = rfSeries;

    const bbUpper = priceChart.addSeries(LineSeries, { color: "#00E5FF", lineWidth: 1, lineStyle: 1, title: "BB Upper", visible: showBB });
    bbUpperRef.current = bbUpper;

    const bbLower = priceChart.addSeries(LineSeries, { color: "#00E5FF", lineWidth: 1, lineStyle: 1, title: "BB Lower", visible: showBB });
    bbLowerRef.current = bbLower;

    const vwapSeries = priceChart.addSeries(LineSeries, { color: "#00E676", lineWidth: 2, title: "VWAP", visible: showVWAP });
    vwapRef.current = vwapSeries;

    const volSeries = volumeChart.addSeries(HistogramSeries, {
      color: "#26a69a",
      priceFormat: { type: "volume" },
    });
    volSeriesRef.current = volSeries;

    // 4. Populate Data
    const formattedCandles = candles.map((c) => ({
      time: (c.timestamp / 1000) as UTCTimestamp,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));
    candSeries.setData(formattedCandles);

    if (candles[0].ema_9 !== undefined) {
      ema9Series.setData(candles.map((c) => ({ time: (c.timestamp / 1000) as UTCTimestamp, value: c.ema_9 || 0 })));
    }
    if (candles[0].ema_21 !== undefined) {
      ema21Series.setData(candles.map((c) => ({ time: (c.timestamp / 1000) as UTCTimestamp, value: c.ema_21 || 0 })));
    }
    if (candles[0].ema_200 !== undefined) {
      ema200Series.setData(candles.map((c) => ({ time: (c.timestamp / 1000) as UTCTimestamp, value: c.ema_200 || 0 })));
    }
    if (candles[0].supertrend !== undefined) {
      stSeries.setData(candles.map((c) => ({ time: (c.timestamp / 1000) as UTCTimestamp, value: c.supertrend || 0 })));
    }
    if (candles[0].range_filter !== undefined) {
      rfSeries.setData(candles.map((c) => ({ time: (c.timestamp / 1000) as UTCTimestamp, value: c.range_filter || 0 })));
    }
    if (candles[0].bb_upper !== undefined) {
      bbUpper.setData(candles.map((c) => ({ time: (c.timestamp / 1000) as UTCTimestamp, value: c.bb_upper || 0 })));
      bbLower.setData(candles.map((c) => ({ time: (c.timestamp / 1000) as UTCTimestamp, value: c.bb_lower || 0 })));
    }
    if (candles[0].vwap !== undefined) {
      vwapSeries.setData(candles.map((c) => ({ time: (c.timestamp / 1000) as UTCTimestamp, value: c.vwap || 0 })));
    }

    volSeries.setData(
      candles.map((c) => ({
        time: (c.timestamp / 1000) as UTCTimestamp,
        value: c.volume,
        color: c.close >= c.open ? "rgba(8, 153, 129, 0.4)" : "rgba(242, 54, 69, 0.4)",
      }))
    );

    // 5. Signal Markers
    const markers: SeriesMarker<UTCTimestamp>[] = [];
    candles.forEach((c) => {
      const timeVal = (c.timestamp / 1000) as UTCTimestamp;
      if (c.range_buy) {
        markers.push({
          time: timeVal,
          position: "belowBar",
          color: "#089981",
          shape: "arrowUp",
          text: "BUY",
        });
      } else if (c.range_sell) {
        markers.push({
          time: timeVal,
          position: "aboveBar",
          color: "#f23645",
          shape: "arrowDown",
          text: "SELL",
        });
      }
    });
    if (markers.length > 0) {
      createSeriesMarkers(candSeries, markers);
    }

    priceChart.timeScale().fitContent();

    // 6. WebSocket Live Ticker
    const wsUrl = `ws://localhost:8000/api/ws/${symbol}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const tick = JSON.parse(event.data);
        if (tick && tick.price !== undefined) {
          const tickTime = (tick.timestamp / 1000) as UTCTimestamp;
          const lastCandle = candles[candles.length - 1];
          if (!lastCandle) return;

          const lastTimeVal = (lastCandle.timestamp / 1000) as UTCTimestamp;
          let updatedCandle: CandleData;

          if (tickTime === lastTimeVal) {
            lastCandle.close = tick.price;
            lastCandle.high = Math.max(lastCandle.high, tick.price);
            lastCandle.low = Math.min(lastCandle.low, tick.price);
            updatedCandle = lastCandle;
          } else {
            updatedCandle = {
              timestamp: tick.timestamp,
              datetime: new Date(tick.timestamp).toISOString(),
              open: tick.price,
              high: tick.price,
              low: tick.price,
              close: tick.price,
              volume: tick.volume_24h || 0,
              ema_9: lastCandle.ema_9,
              ema_21: lastCandle.ema_21,
              ema_200: lastCandle.ema_200,
              supertrend: lastCandle.supertrend,
              range_filter: lastCandle.range_filter,
              bb_upper: lastCandle.bb_upper,
              bb_lower: lastCandle.bb_lower,
              vwap: lastCandle.vwap
            };
            candles.push(updatedCandle);
          }

          candSeries.update({
            time: (updatedCandle.timestamp / 1000) as UTCTimestamp,
            open: updatedCandle.open,
            high: updatedCandle.high,
            low: updatedCandle.low,
            close: updatedCandle.close,
          });

          volSeries.update({
            time: (updatedCandle.timestamp / 1000) as UTCTimestamp,
            value: updatedCandle.volume,
            color: updatedCandle.close >= updatedCandle.open ? "rgba(8, 153, 129, 0.4)" : "rgba(242, 54, 69, 0.4)",
          });
        }
      } catch (err) {
        console.error("WebSocket tick error:", err);
      }
    };

    const handleResize = () => {
      if (priceChart && chartContainerRef.current) {
        priceChart.resize(chartContainerRef.current.clientWidth, 380);
      }
      if (volumeChart && volumeContainerRef.current) {
        volumeChart.resize(volumeContainerRef.current.clientWidth, 90);
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      priceChart.remove();
      volumeChart.remove();
      if (wsRef.current) wsRef.current.close();
    };
  }, [candles, symbol, showEMA9, showEMA21, showEMA200, showSupertrend, showRangeFilter, showBB, showVWAP]);

  return (
    <div style={{ display: "flex", flexDirection: "column", width: "100%", backgroundColor: "#131722", borderRadius: "6px", overflow: "hidden" }}>
      {/* Overlay Toolbar Switches */}
      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", padding: "6px 12px", borderBottom: "1px solid #2a2e39", backgroundColor: "#181c27", alignItems: "center" }}>
        <span style={{ fontSize: "11px", color: "#787b86", fontWeight: 700, marginRight: "4px" }}>OVERLAYS:</span>

        <button
          className={`overlay-chip ${showEMA9 ? "active blue" : ""}`}
          onClick={() => setShowEMA9((v) => !v)}
        >
          EMA 9
        </button>

        <button
          className={`overlay-chip ${showEMA21 ? "active orange" : ""}`}
          onClick={() => setShowEMA21((v) => !v)}
        >
          EMA 21
        </button>

        <button
          className={`overlay-chip ${showEMA200 ? "active purple" : ""}`}
          onClick={() => setShowEMA200((v) => !v)}
        >
          EMA 200
        </button>

        <button
          className={`overlay-chip ${showSupertrend ? "active magenta" : ""}`}
          onClick={() => setShowSupertrend((v) => !v)}
        >
          Supertrend
        </button>

        <button
          className={`overlay-chip ${showRangeFilter ? "active yellow" : ""}`}
          onClick={() => setShowRangeFilter((v) => !v)}
        >
          Range Filter
        </button>

        <button
          className={`overlay-chip ${showBB ? "active cyan" : ""}`}
          onClick={() => setShowBB((v) => !v)}
        >
          Bollinger
        </button>

        <button
          className={`overlay-chip ${showVWAP ? "active green" : ""}`}
          onClick={() => setShowVWAP((v) => !v)}
        >
          VWAP
        </button>
      </div>

      <div ref={chartContainerRef} style={{ width: "100%", height: "380px" }} />
      <div ref={volumeContainerRef} style={{ width: "100%", height: "90px", borderTop: "1px solid #2a2e39" }} />
    </div>
  );
};
