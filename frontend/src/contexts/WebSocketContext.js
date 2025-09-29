import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { message, notification } from 'antd';
import { useAuth } from './AuthContext';

const WebSocketContext = createContext();

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};

export const WebSocketProvider = ({ children }) => {
  const { user, token } = useAuth();
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [lastMessage, setLastMessage] = useState(null);
  const [subscribers, setSubscribers] = useState({});
  
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const reconnectDelay = 3000;

  // WebSocket URL
  const getWebSocketUrl = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = process.env.REACT_APP_API_URL 
      ? process.env.REACT_APP_API_URL.replace(/^https?:\/\//, '').replace(/\/$/, '')
      : window.location.host;
    return `${protocol}//${host}/ws`;
  };

  // Connect to WebSocket
  const connect = () => {
    if (!user || !token) {
      console.log('No user or token available for WebSocket connection');
      return;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }

    try {
      setConnectionStatus('connecting');
      const wsUrl = `${getWebSocketUrl()}?token=${token}`;
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setConnectionStatus('connected');
        reconnectAttempts.current = 0;
        
        // Send authentication message
        send({
          type: 'auth',
          token: token
        });
      };

      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('WebSocket message received:', data);
          
          setLastMessage(data);
          handleMessage(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      wsRef.current.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        setIsConnected(false);
        setConnectionStatus('disconnected');
        
        // Attempt to reconnect if not a normal closure
        if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          scheduleReconnect();
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus('error');
      };

    } catch (error) {
      console.error('Error creating WebSocket connection:', error);
      setConnectionStatus('error');
    }
  };

  // Disconnect WebSocket
  const disconnect = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Manual disconnect');
      wsRef.current = null;
    }

    setIsConnected(false);
    setConnectionStatus('disconnected');
    reconnectAttempts.current = 0;
  };

  // Schedule reconnection
  const scheduleReconnect = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    reconnectAttempts.current++;
    const delay = reconnectDelay * Math.pow(2, reconnectAttempts.current - 1);
    
    console.log(`Scheduling reconnect attempt ${reconnectAttempts.current} in ${delay}ms`);
    setConnectionStatus('reconnecting');

    reconnectTimeoutRef.current = setTimeout(() => {
      connect();
    }, delay);
  };

  // Send message through WebSocket
  const send = (message) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
      return true;
    } else {
      console.warn('WebSocket not connected, cannot send message:', message);
      return false;
    }
  };

  // Handle incoming messages
  const handleMessage = (data) => {
    const { type, payload } = data;

    // Notify subscribers
    if (subscribers[type]) {
      subscribers[type].forEach(callback => {
        try {
          callback(payload);
        } catch (error) {
          console.error('Error in WebSocket subscriber callback:', error);
        }
      });
    }

    // Handle specific message types
    switch (type) {
      case 'alarm':
        handleAlarmMessage(payload);
        break;
      case 'performance_update':
        handlePerformanceUpdate(payload);
        break;
      case 'ont_status_change':
        handleONTStatusChange(payload);
        break;
      case 'system_notification':
        handleSystemNotification(payload);
        break;
      case 'auth_error':
        handleAuthError(payload);
        break;
      default:
        console.log('Unhandled WebSocket message type:', type);
    }
  };

  // Handle alarm messages
  const handleAlarmMessage = (alarm) => {
    const severity = alarm.severity?.toLowerCase() || 'info';
    const title = `Alarm: ${alarm.type || 'Unknown'}`;
    const description = alarm.description || alarm.message || 'No description available';

    notification[severity]({
      message: title,
      description: description,
      duration: severity === 'critical' ? 0 : 4.5,
      placement: 'topRight',
    });
  };

  // Handle performance updates
  const handlePerformanceUpdate = (data) => {
    // This will be handled by subscribers (charts, monitoring components)
    console.log('Performance update received:', data);
  };

  // Handle ONT status changes
  const handleONTStatusChange = (data) => {
    const { ont_id, old_status, new_status } = data;
    
    if (old_status !== new_status) {
      const statusColor = new_status === 'online' ? 'success' : 'warning';
      message[statusColor](`ONT ${ont_id} status changed: ${old_status} → ${new_status}`);
    }
  };

  // Handle system notifications
  const handleSystemNotification = (data) => {
    const { level, title, message: msg } = data;
    
    notification[level || 'info']({
      message: title || 'System Notification',
      description: msg,
      duration: 4.5,
      placement: 'topRight',
    });
  };

  // Handle authentication errors
  const handleAuthError = (data) => {
    console.error('WebSocket authentication error:', data);
    message.error('WebSocket authentication failed. Please refresh the page.');
    disconnect();
  };

  // Subscribe to message types
  const subscribe = (messageType, callback) => {
    setSubscribers(prev => ({
      ...prev,
      [messageType]: [...(prev[messageType] || []), callback]
    }));

    // Return unsubscribe function
    return () => {
      setSubscribers(prev => ({
        ...prev,
        [messageType]: (prev[messageType] || []).filter(cb => cb !== callback)
      }));
    };
  };

  // Subscribe to multiple message types
  const subscribeMultiple = (messageTypes, callback) => {
    const unsubscribeFunctions = messageTypes.map(type => subscribe(type, callback));
    
    return () => {
      unsubscribeFunctions.forEach(unsubscribe => unsubscribe());
    };
  };

  // Effect to handle connection based on auth state
  useEffect(() => {
    if (user && token) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [user, token]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, []);

  const value = {
    isConnected,
    connectionStatus,
    lastMessage,
    connect,
    disconnect,
    send,
    subscribe,
    subscribeMultiple
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};