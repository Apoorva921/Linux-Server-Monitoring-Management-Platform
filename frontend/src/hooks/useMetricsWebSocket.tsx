import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import type { WsEvent } from '../types';
import { useAuth } from './AuthContext';

export type ConnectionState = 'connected' | 'connecting' | 'disconnected';
type EventListener = (event: WsEvent) => void;

interface WsContextValue {
  connectionState: ConnectionState;
  lastEventAt: string | null;
  addListener: (listener: EventListener) => () => void;
  subscribeTopic: (serverId: string) => void;
  unsubscribeTopic: (serverId: string) => void;
}

const WsContext = createContext<WsContextValue | null>(null);

function resolveWsUrl(token: string): string {
  const explicit = import.meta.env.VITE_WS_URL;
  if (explicit) {
    return `${explicit.replace(/\/$/, '')}/ws/metrics?token=${encodeURIComponent(token)}`;
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/ws/metrics?token=${encodeURIComponent(token)}`;
}

export const WebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { token } = useAuth();
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [lastEventAt, setLastEventAt] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const listenersRef = useRef<Set<EventListener>>(new Set());
  const topicsRef = useRef<Set<string>>(new Set(['all']));
  const reconnectTimerRef = useRef<number | null>(null);
  const pingTimerRef = useRef<number | null>(null);
  const retryCountRef = useRef<number>(0);

  const addListener = useCallback((listener: EventListener) => {
    listenersRef.current.add(listener);
    return () => {
      listenersRef.current.delete(listener);
    };
  }, []);

  const subscribeTopic = useCallback((serverId: string) => {
    if (topicsRef.current.has(serverId)) return; // Prevent duplicate subscriptions
    topicsRef.current.add(serverId);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'subscribe', server_id: serverId }));
    }
  }, []);

  const unsubscribeTopic = useCallback((serverId: string) => {
    if (!topicsRef.current.has(serverId) || serverId === 'all') return;
    topicsRef.current.delete(serverId);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'unsubscribe', server_id: serverId }));
    }
  }, []);

  useEffect(() => {
    if (!token) {
      setConnectionState('disconnected');
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      return;
    }

    let cancelled = false;

    const connect = () => {
      if (cancelled) return;
      setConnectionState('connecting');
      const socket = new WebSocket(resolveWsUrl(token));
      wsRef.current = socket;

      socket.onopen = () => {
        if (cancelled) return;
        retryCountRef.current = 0;
        setConnectionState('connected');
        topicsRef.current.forEach((topic) => {
          if (topic !== 'all') {
            socket.send(JSON.stringify({ action: 'subscribe', server_id: topic }));
          }
        });
        if (pingTimerRef.current) window.clearInterval(pingTimerRef.current);
        pingTimerRef.current = window.setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ action: 'ping' }));
          }
        }, 25000);
      };

      socket.onmessage = (evt) => {
        try {
          const parsed = JSON.parse(evt.data) as WsEvent;
          if (parsed.type !== 'pong') {
            setLastEventAt(new Date().toISOString());
          }
          listenersRef.current.forEach((fn) => fn(parsed));
        } catch {
          // Ignore malformed frame
        }
      };

      socket.onerror = () => {
        socket.close();
      };

      socket.onclose = () => {
        if (pingTimerRef.current) {
          window.clearInterval(pingTimerRef.current);
          pingTimerRef.current = null;
        }
        if (cancelled) return;
        setConnectionState('disconnected');
        const delayMs = Math.min(30000, 1000 * Math.pow(2, retryCountRef.current));
        retryCountRef.current += 1;
        reconnectTimerRef.current = window.setTimeout(connect, delayMs);
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimerRef.current) window.clearTimeout(reconnectTimerRef.current);
      if (pingTimerRef.current) window.clearInterval(pingTimerRef.current);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [token]);

  return (
    <WsContext.Provider
      value={{ connectionState, lastEventAt, addListener, subscribeTopic, unsubscribeTopic }}
    >
      {children}
    </WsContext.Provider>
  );
};

export function useMetricsWebSocket(): WsContextValue {
  const ctx = useContext(WsContext);
  if (!ctx) throw new Error('useMetricsWebSocket must be used inside WebSocketProvider');
  return ctx;
}

