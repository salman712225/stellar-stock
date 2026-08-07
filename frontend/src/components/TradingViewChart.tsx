import React, { useEffect, useRef } from "react";
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
  ema_9: number;
  ema_21: number;
  supertrend: number;
  range_filter?: number;
  range_buy?: boolean;
  range_sell?: boolean;
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
  
  const candSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const ema9SeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const ema21SeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const stSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const rfSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const volSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);

  // WebSocket reference
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current || !volumeContainerRef.current || candles.length === 0) return;

    // Reset containers
    chartContainerRef.current.innerHTML = "";
    volumeContainerRef.current.innerHTML = "";

    // 1. Initialize Price Chart
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

    // 2. Initialize Volume Chart
    const volumeChart = createChart(volumeContainerRef.current, {
      width: volumeContainerRef.current.clientWidth,
      height: 100,
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
        visible: false, // hide time scale to stack it directly below price chart
        borderColor: "#2a2e39",
      },
    });
    volumeChartRef.current = volumeChart;

    // 3. Synchronize time scales
    priceChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      if (range) volumeChart.timeScale().setVisibleLogicalRange(range);
    });
    volumeChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      if (range) priceChart.timeScale().setVisibleLogicalRange(range);
    });

    // 4. Create series
    const candSeries = priceChart.addSeries(CandlestickSeries, {
      upColor: "#089981",
      downColor: "#f23645",
      borderVisible: false,
      wickUpColor: "#089981",
      wickDownColor: "#f23645",
    });
    candSeriesRef.current = candSeries;

    const ema9Series = priceChart.addSeries(LineSeries, { color: "#2196F3", lineWidth: 2, title: "EMA 9" });
    ema9SeriesRef.current = ema9Series;

    const ema21Series = priceChart.addSeries(LineSeries, { color: "#FF9800", lineWidth: 2, title: "EMA 21" });
    ema21SeriesRef.current = ema21Series;

    const stSeries = priceChart.addSeries(LineSeries, { color: "#E040FB", lineWidth: 2, lineStyle: 2, title: "Supertrend" });
    stSeriesRef.current = stSeries;

    const rfSeries = priceChart.addSeries(LineSeries, { color: "#FFCA28", lineWidth: 2, title: "Range Filter" });
    rfSeriesRef.current = rfSeries;

    const volSeries = volumeChart.addSeries(HistogramSeries, {
      color: "#26a69a",
      priceFormat: { type: "volume" },
    });
    volSeriesRef.current = volSeries;

    // 5. Map and set data
    // Format timestamp: Lightweight charts expects seconds since epoch (UTC)
    const formattedCandles = candles.map((c) => ({
      time: (c.timestamp / 1000) as UTCTimestamp,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));
    candSeries.setData(formattedCandles);

    ema9Series.setData(candles.map((c) => ({ time: (c.timestamp / 1000) as UTCTimestamp, value: c.ema_9 })));
    ema21Series.setData(candles.map((c) => ({ time: (c.timestamp / 1000) as UTCTimestamp, value: c.ema_21 })));
    stSeries.setData(candles.map((c) => ({ time: (c.timestamp / 1000) as UTCTimestamp, value: c.supertrend })));
    
    if (candles[0].range_filter !== undefined) {
      rfSeries.setData(candles.map((c) => ({ time: (c.timestamp / 1000) as UTCTimestamp, value: c.range_filter || 0 })));
    }

    volSeries.setData(
      candles.map((c) => ({
        time: (c.timestamp / 1000) as UTCTimestamp,
        value: c.volume,
        color: c.close >= c.open ? "rgba(8, 153, 129, 0.4)" : "rgba(242, 54, 69, 0.4)",
      }))
    );

    // 6. Set Range Filter signals markers on candles
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

    // Fit content
    priceChart.timeScale().fitContent();

    // 7. WebSocket Live Updates Listener
    const wsUrl = `ws://localhost:8000/api/ws/${symbol}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const tick = JSON.parse(event.data);
        if (tick && tick.price !== undefined) {
          const tickTime = (tick.timestamp / 1000) as UTCTimestamp;
          
          // Get last candle to update or insert
          const lastCandle = candles[candles.length - 1];
          if (!lastCandle) return;

          const lastTimeVal = (lastCandle.timestamp / 1000) as UTCTimestamp;
          
          let updatedCandle;
          if (tickTime === lastTimeVal) {
            // Update last candle close, high, low
            lastCandle.close = tick.price;
            lastCandle.high = Math.max(lastCandle.high, tick.price);
            lastCandle.low = Math.min(lastCandle.low, tick.price);
            updatedCandle = lastCandle;
          } else {
            // New candle started
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
              supertrend: lastCandle.supertrend,
              range_filter: lastCandle.range_filter,
            };
            // Append
            candles.push(updatedCandle);
          }

          // Update chart series
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
        console.error("Error handling ws ticket update:", err);
      }
    };

    ws.onclose = () => {
      console.log(`WebSocket closed for ${symbol}`);
    };

    // Handle resizing
    const handleResize = () => {
      if (priceChart && chartContainerRef.current) {
        priceChart.resize(chartContainerRef.current.clientWidth, 380);
      }
      if (volumeChart && volumeContainerRef.current) {
        volumeChart.resize(volumeContainerRef.current.clientWidth, 100);
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      priceChart.remove();
      volumeChart.remove();
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [candles, symbol]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "2px", width: "100%", backgroundColor: "#131722" }}>
      <div ref={chartContainerRef} style={{ width: "100%", height: "380px" }} />
      <div ref={volumeContainerRef} style={{ width: "100%", height: "100px", borderTop: "1px solid #2a2e39" }} />
    </div>
  );
};
