// Centralized API and WebSocket configuration
export const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");

export const getWsUrl = (path: string): string => {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  
  if (import.meta.env.VITE_WS_URL) {
    const base = import.meta.env.VITE_WS_URL.replace(/\/$/, "");
    return `${base}${cleanPath}`;
  }
  
  // Derive WebSocket protocol and host automatically from API_URL
  const isHttps = API_URL.startsWith("https://");
  const wsProtocol = isHttps ? "wss://" : "ws://";
  const host = API_URL.replace(/^https?:\/\//, "");
  
  return `${wsProtocol}${host}${cleanPath}`;
};
