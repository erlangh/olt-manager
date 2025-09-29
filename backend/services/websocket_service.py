"""
WebSocket service for real-time updates.
"""

import json
import logging
import asyncio
from typing import Dict, List, Set, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """WebSocket message types."""
    # System messages
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"
    
    # Authentication
    AUTH = "auth"
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILED = "auth_failed"
    
    # Device updates
    OLT_STATUS = "olt_status"
    ONT_STATUS = "ont_status"
    PORT_STATUS = "port_status"
    
    # Performance data
    PERFORMANCE_DATA = "performance_data"
    METRICS_UPDATE = "metrics_update"
    
    # Alarms and notifications
    ALARM = "alarm"
    NOTIFICATION = "notification"
    
    # Configuration changes
    CONFIG_CHANGE = "config_change"
    
    # Discovery events
    DEVICE_DISCOVERED = "device_discovered"
    DEVICE_LOST = "device_lost"
    
    # Subscription management
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    SUBSCRIPTION_CONFIRMED = "subscription_confirmed"


@dataclass
class WebSocketMessage:
    """WebSocket message structure."""
    type: MessageType
    data: Any
    timestamp: datetime = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "session_id": self.session_id
        }
    
    def to_json(self) -> str:
        """Convert message to JSON string."""
        return json.dumps(self.to_dict(), default=str)


@dataclass
class ClientConnection:
    """WebSocket client connection info."""
    websocket: WebSocket
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    subscriptions: Set[str] = None
    connected_at: datetime = None
    last_ping: datetime = None
    
    def __post_init__(self):
        if self.subscriptions is None:
            self.subscriptions = set()
        if self.connected_at is None:
            self.connected_at = datetime.utcnow()
        if self.last_ping is None:
            self.last_ping = datetime.utcnow()
    
    @property
    def is_authenticated(self) -> bool:
        """Check if client is authenticated."""
        return self.user_id is not None
    
    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is still connected."""
        return self.websocket.client_state == WebSocketState.CONNECTED


class WebSocketManager:
    """WebSocket connection manager."""
    
    def __init__(self):
        self.connections: Dict[str, ClientConnection] = {}
        self.user_connections: Dict[str, Set[str]] = {}  # user_id -> set of connection_ids
        self.subscription_groups: Dict[str, Set[str]] = {}  # topic -> set of connection_ids
        self._connection_counter = 0
        self._cleanup_task = None
    
    def start_cleanup_task(self):
        """Start background cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_connections())
    
    def stop_cleanup_task(self):
        """Stop background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None
    
    async def _cleanup_connections(self):
        """Cleanup disconnected connections periodically."""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                disconnected_ids = []
                for conn_id, connection in self.connections.items():
                    if not connection.is_connected:
                        disconnected_ids.append(conn_id)
                
                for conn_id in disconnected_ids:
                    await self._remove_connection(conn_id)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
    
    async def connect(self, websocket: WebSocket) -> str:
        """Accept new WebSocket connection."""
        await websocket.accept()
        
        # Generate unique connection ID
        self._connection_counter += 1
        connection_id = f"conn_{self._connection_counter}_{datetime.utcnow().timestamp()}"
        
        # Create connection object
        connection = ClientConnection(
            websocket=websocket,
            session_id=connection_id
        )
        
        self.connections[connection_id] = connection
        
        # Send connection confirmation
        message = WebSocketMessage(
            type=MessageType.CONNECT,
            data={"connection_id": connection_id, "status": "connected"},
            session_id=connection_id
        )
        
        await self._send_to_connection(connection_id, message)
        
        logger.info(f"WebSocket connection established: {connection_id}")
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """Handle WebSocket disconnection."""
        await self._remove_connection(connection_id)
        logger.info(f"WebSocket connection closed: {connection_id}")
    
    async def _remove_connection(self, connection_id: str):
        """Remove connection and cleanup references."""
        if connection_id not in self.connections:
            return
        
        connection = self.connections[connection_id]
        
        # Remove from user connections
        if connection.user_id and connection.user_id in self.user_connections:
            self.user_connections[connection.user_id].discard(connection_id)
            if not self.user_connections[connection.user_id]:
                del self.user_connections[connection.user_id]
        
        # Remove from subscription groups
        for topic in connection.subscriptions:
            if topic in self.subscription_groups:
                self.subscription_groups[topic].discard(connection_id)
                if not self.subscription_groups[topic]:
                    del self.subscription_groups[topic]
        
        # Remove connection
        del self.connections[connection_id]
    
    async def authenticate(self, connection_id: str, user_id: str) -> bool:
        """Authenticate WebSocket connection."""
        if connection_id not in self.connections:
            return False
        
        connection = self.connections[connection_id]
        connection.user_id = user_id
        
        # Add to user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        
        # Send authentication success
        message = WebSocketMessage(
            type=MessageType.AUTH_SUCCESS,
            data={"user_id": user_id},
            user_id=user_id,
            session_id=connection_id
        )
        
        await self._send_to_connection(connection_id, message)
        logger.info(f"WebSocket authenticated for user: {user_id}")
        return True
    
    async def subscribe(self, connection_id: str, topic: str) -> bool:
        """Subscribe connection to a topic."""
        if connection_id not in self.connections:
            return False
        
        connection = self.connections[connection_id]
        connection.subscriptions.add(topic)
        
        # Add to subscription group
        if topic not in self.subscription_groups:
            self.subscription_groups[topic] = set()
        self.subscription_groups[topic].add(connection_id)
        
        # Send subscription confirmation
        message = WebSocketMessage(
            type=MessageType.SUBSCRIPTION_CONFIRMED,
            data={"topic": topic, "status": "subscribed"},
            user_id=connection.user_id,
            session_id=connection_id
        )
        
        await self._send_to_connection(connection_id, message)
        logger.info(f"Connection {connection_id} subscribed to {topic}")
        return True
    
    async def unsubscribe(self, connection_id: str, topic: str) -> bool:
        """Unsubscribe connection from a topic."""
        if connection_id not in self.connections:
            return False
        
        connection = self.connections[connection_id]
        connection.subscriptions.discard(topic)
        
        # Remove from subscription group
        if topic in self.subscription_groups:
            self.subscription_groups[topic].discard(connection_id)
            if not self.subscription_groups[topic]:
                del self.subscription_groups[topic]
        
        logger.info(f"Connection {connection_id} unsubscribed from {topic}")
        return True
    
    async def _send_to_connection(self, connection_id: str, message: WebSocketMessage):
        """Send message to specific connection."""
        if connection_id not in self.connections:
            return False
        
        connection = self.connections[connection_id]
        
        if not connection.is_connected:
            await self._remove_connection(connection_id)
            return False
        
        try:
            await connection.websocket.send_text(message.to_json())
            return True
        except Exception as e:
            logger.error(f"Error sending message to {connection_id}: {e}")
            await self._remove_connection(connection_id)
            return False
    
    async def send_to_user(self, user_id: str, message: WebSocketMessage):
        """Send message to all connections of a user."""
        if user_id not in self.user_connections:
            return 0
        
        connection_ids = list(self.user_connections[user_id])
        sent_count = 0
        
        for connection_id in connection_ids:
            message.user_id = user_id
            message.session_id = connection_id
            
            if await self._send_to_connection(connection_id, message):
                sent_count += 1
        
        return sent_count
    
    async def broadcast_to_topic(self, topic: str, message: WebSocketMessage):
        """Broadcast message to all subscribers of a topic."""
        if topic not in self.subscription_groups:
            return 0
        
        connection_ids = list(self.subscription_groups[topic])
        sent_count = 0
        
        for connection_id in connection_ids:
            if connection_id in self.connections:
                connection = self.connections[connection_id]
                message.user_id = connection.user_id
                message.session_id = connection_id
                
                if await self._send_to_connection(connection_id, message):
                    sent_count += 1
        
        return sent_count
    
    async def broadcast_to_all(self, message: WebSocketMessage):
        """Broadcast message to all connected clients."""
        connection_ids = list(self.connections.keys())
        sent_count = 0
        
        for connection_id in connection_ids:
            connection = self.connections[connection_id]
            message.user_id = connection.user_id
            message.session_id = connection_id
            
            if await self._send_to_connection(connection_id, message):
                sent_count += 1
        
        return sent_count
    
    async def handle_message(self, connection_id: str, message_data: str):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message_data)
            message_type = MessageType(data.get("type"))
            message_data = data.get("data", {})
            
            if message_type == MessageType.PING:
                await self._handle_ping(connection_id)
            elif message_type == MessageType.SUBSCRIBE:
                topic = message_data.get("topic")
                if topic:
                    await self.subscribe(connection_id, topic)
            elif message_type == MessageType.UNSUBSCRIBE:
                topic = message_data.get("topic")
                if topic:
                    await self.unsubscribe(connection_id, topic)
            else:
                logger.warning(f"Unhandled message type: {message_type}")
        
        except Exception as e:
            logger.error(f"Error handling message from {connection_id}: {e}")
            
            # Send error response
            error_message = WebSocketMessage(
                type=MessageType.ERROR,
                data={"error": "Invalid message format"},
                session_id=connection_id
            )
            await self._send_to_connection(connection_id, error_message)
    
    async def _handle_ping(self, connection_id: str):
        """Handle ping message."""
        if connection_id in self.connections:
            connection = self.connections[connection_id]
            connection.last_ping = datetime.utcnow()
            
            # Send pong response
            pong_message = WebSocketMessage(
                type=MessageType.PONG,
                data={"timestamp": datetime.utcnow().isoformat()},
                user_id=connection.user_id,
                session_id=connection_id
            )
            await self._send_to_connection(connection_id, pong_message)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        total_connections = len(self.connections)
        authenticated_connections = sum(1 for conn in self.connections.values() if conn.is_authenticated)
        unique_users = len(self.user_connections)
        total_subscriptions = sum(len(conn.subscriptions) for conn in self.connections.values())
        
        return {
            "total_connections": total_connections,
            "authenticated_connections": authenticated_connections,
            "unique_users": unique_users,
            "total_subscriptions": total_subscriptions,
            "subscription_topics": list(self.subscription_groups.keys())
        }


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


class NotificationService:
    """Service for sending notifications via WebSocket."""
    
    def __init__(self, ws_manager: WebSocketManager = None):
        self.ws_manager = ws_manager or websocket_manager
    
    async def send_olt_status_update(self, olt_id: str, status_data: Dict[str, Any]):
        """Send OLT status update."""
        message = WebSocketMessage(
            type=MessageType.OLT_STATUS,
            data={
                "olt_id": olt_id,
                "status": status_data
            }
        )
        
        topic = f"olt.{olt_id}.status"
        await self.ws_manager.broadcast_to_topic(topic, message)
        
        # Also broadcast to general OLT topic
        await self.ws_manager.broadcast_to_topic("olt.status", message)
    
    async def send_ont_status_update(self, ont_id: str, olt_id: str, status_data: Dict[str, Any]):
        """Send ONT status update."""
        message = WebSocketMessage(
            type=MessageType.ONT_STATUS,
            data={
                "ont_id": ont_id,
                "olt_id": olt_id,
                "status": status_data
            }
        )
        
        topic = f"ont.{ont_id}.status"
        await self.ws_manager.broadcast_to_topic(topic, message)
        
        # Also broadcast to OLT-specific ONT topic
        olt_topic = f"olt.{olt_id}.ont.status"
        await self.ws_manager.broadcast_to_topic(olt_topic, message)
    
    async def send_performance_data(self, device_id: str, device_type: str, metrics: Dict[str, Any]):
        """Send performance data update."""
        message = WebSocketMessage(
            type=MessageType.PERFORMANCE_DATA,
            data={
                "device_id": device_id,
                "device_type": device_type,
                "metrics": metrics
            }
        )
        
        topic = f"{device_type}.{device_id}.metrics"
        await self.ws_manager.broadcast_to_topic(topic, message)
        
        # Also broadcast to general metrics topic
        await self.ws_manager.broadcast_to_topic("metrics", message)
    
    async def send_alarm(self, alarm_data: Dict[str, Any]):
        """Send alarm notification."""
        message = WebSocketMessage(
            type=MessageType.ALARM,
            data=alarm_data
        )
        
        # Broadcast to alarm subscribers
        await self.ws_manager.broadcast_to_topic("alarms", message)
        
        # Send to specific device subscribers if device info is available
        if "device_id" in alarm_data and "device_type" in alarm_data:
            device_topic = f"{alarm_data['device_type']}.{alarm_data['device_id']}.alarms"
            await self.ws_manager.broadcast_to_topic(device_topic, message)
    
    async def send_notification(self, notification_data: Dict[str, Any], user_id: str = None):
        """Send general notification."""
        message = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            data=notification_data
        )
        
        if user_id:
            # Send to specific user
            await self.ws_manager.send_to_user(user_id, message)
        else:
            # Broadcast to all notification subscribers
            await self.ws_manager.broadcast_to_topic("notifications", message)
    
    async def send_device_discovery(self, device_data: Dict[str, Any], discovered: bool = True):
        """Send device discovery notification."""
        message_type = MessageType.DEVICE_DISCOVERED if discovered else MessageType.DEVICE_LOST
        
        message = WebSocketMessage(
            type=message_type,
            data=device_data
        )
        
        # Broadcast to discovery subscribers
        await self.ws_manager.broadcast_to_topic("discovery", message)
    
    async def send_config_change(self, config_data: Dict[str, Any]):
        """Send configuration change notification."""
        message = WebSocketMessage(
            type=MessageType.CONFIG_CHANGE,
            data=config_data
        )
        
        # Broadcast to configuration subscribers
        await self.ws_manager.broadcast_to_topic("config", message)
        
        # Send to specific device subscribers if device info is available
        if "device_id" in config_data and "device_type" in config_data:
            device_topic = f"{config_data['device_type']}.{config_data['device_id']}.config"
            await self.ws_manager.broadcast_to_topic(device_topic, message)


# Global notification service instance
notification_service = NotificationService()