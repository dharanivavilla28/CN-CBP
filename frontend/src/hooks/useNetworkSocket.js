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

  const connect = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/network`;

    try {
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          setLastMessage(payload);
          if (onEventReceived) {
            onEventReceived(payload);
          }
        } catch (err) {
          console.error('Failed to parse WS payload', err);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        // Attempt reconnect after 2 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 2000);
      };

      ws.onerror = (err) => {
        console.warn('WebSocket encountered error:', err);
        ws.close();
      };
    } catch (e) {
      console.error('WebSocket connection error:', e);
      reconnectTimeoutRef.current = setTimeout(connect, 3000);
    }
  }, [onEventReceived]);

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
