/**
 * WebSocket Connection & Live Event Streaming Hook
 * Part of: ML-Enhanced SDN Emergency Communication Network
 */
import { useEffect, useRef, useState, useCallback } from 'react';

export function useNetworkSocket(onEventReceived) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const onEventRef = useRef(onEventReceived);

  useEffect(() => {
    onEventRef.current = onEventReceived;
  }, [onEventReceived]);

  const connect = useCallback(() => {
    const isDev = window.location.port === '5173';
    const wsUrl = isDev
      ? `ws://${window.location.hostname || 'localhost'}:8000/ws/network`
      : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/network`;

    try {
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        return;
      }
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          setLastMessage(payload);
          if (onEventRef.current) {
            onEventRef.current(payload);
          }
        } catch (err) {
          console.error('Failed to parse WS payload', err);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 2000);
      };

      ws.onerror = (err) => {
        console.warn('WebSocket encountered error, reconnecting...', err);
        try {
          ws.close();
        } catch (_) {}
      };
    } catch (e) {
      console.error('WebSocket connection error:', e);
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = setTimeout(connect, 3000);
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (socketRef.current) socketRef.current.close();
    };
  }, [connect]);

  const send = useCallback((action, data = {}) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ action, ...data }));
    }
  }, []);

  return { isConnected, lastMessage, send };
}
