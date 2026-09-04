// Centralized API and WebSocket configuration with browser persistence support

export const getApiUrl = (): string => {
  if (typeof window !== "undefined") {
    const savedUrl = localStorage.getItem("stellar_backend_url");
    if (savedUrl && savedUrl.trim()) {
      return savedUrl.trim().replace(/\/$/, "");
    }
  }
  return (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
};

export const setCustomApiUrl = (url: string): void => {
  if (typeof window !== "undefined") {
    if (url && url.trim()) {
      localStorage.setItem("stellar_backend_url", url.trim().replace(/\/$/, ""));
    } else {
      localStorage.removeItem("stellar_backend_url");
    }
  }
};

// Dynamic export for API_URL
export const API_URL = getApiUrl();

export const getWsUrl = (path: string): string => {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  
  if (import.meta.env.VITE_WS_URL) {
    const base = import.meta.env.VITE_WS_URL.replace(/\/$/, "");
    return `${base}${cleanPath}`;
  }
  
  const currentApiUrl = getApiUrl();
  const isHttps = currentApiUrl.startsWith("https://");
  const wsProtocol = isHttps ? "wss://" : "ws://";
  const host = currentApiUrl.replace(/^https?:\/\//, "");
  
  return `${wsProtocol}${host}${cleanPath}`;
};
