"""
WebSocket API endpoints for real-time communication.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import json
import logging

from ..auth.jwt_handler import verify_token
from ..auth.dependencies import get_current_user
from ..models.user import User
from ..services.websocket_service import websocket_manager, MessageType
from ..database.connection import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/ws", tags=["websocket"])
security = HTTPBearer()
logger = logging.getLogger(__name__)


async def get_user_from_token(token: str, db: Session) -> Optional[User]:
    """Get user from JWT token for WebSocket authentication."""
    try:
        payload = verify_token(token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        user = db.query(User).filter(User.id == user_id).first()
        return user if user and user.is_active else None
        
    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        return None


@router.websocket("/connect")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token"),
    db: Session = Depends(get_db)
):
    """Main WebSocket endpoint for real-time communication."""
    
    # Authenticate user
    user = await get_user_from_token(token, db)
    if not user:
        await websocket.close(code=4001, reason="Authentication failed")
        return
    
    # Accept connection
    await websocket.accept()
    
    # Add connection to manager
    connection_id = await websocket_manager.connect(websocket, user.id, user.username)
    
    try:
        # Send welcome message
        await websocket_manager.send_personal_message(
            connection_id,
            {
                "type": MessageType.NOTIFICATION.value,
                "data": {
                    "message": f"Welcome {user.username}! Connected successfully.",
                    "connection_id": connection_id,
                    "timestamp": websocket_manager._get_current_time()
                }
            }
        )
        
        # Listen for messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Process message based on type
                await process_websocket_message(connection_id, message, user)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for user {user.username}")
                break
            except json.JSONDecodeError:
                await websocket_manager.send_personal_message(
                    connection_id,
                    {
                        "type": MessageType.ERROR.value,
                        "data": {
                            "message": "Invalid JSON format",
                            "timestamp": websocket_manager._get_current_time()
                        }
                    }
                )
            except Exception as e:
                logger.error(f"WebSocket message processing error: {e}")
                await websocket_manager.send_personal_message(
                    connection_id,
                    {
                        "type": MessageType.ERROR.value,
                        "data": {
                            "message": f"Message processing error: {str(e)}",
                            "timestamp": websocket_manager._get_current_time()
                        }
                    }
                )
    
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    
    finally:
        # Remove connection
        await websocket_manager.disconnect(connection_id)


async def process_websocket_message(connection_id: str, message: Dict[str, Any], user: User):
    """Process incoming WebSocket messages."""
    
    message_type = message.get("type")
    data = message.get("data", {})
    
    if message_type == "subscribe":
        # Subscribe to specific topics
        topics = data.get("topics", [])
        for topic in topics:
            await websocket_manager.subscribe_to_topic(connection_id, topic)
        
        await websocket_manager.send_personal_message(
            connection_id,
            {
                "type": MessageType.NOTIFICATION.value,
                "data": {
                    "message": f"Subscribed to topics: {', '.join(topics)}",
                    "timestamp": websocket_manager._get_current_time()
                }
            }
        )
    
    elif message_type == "unsubscribe":
        # Unsubscribe from specific topics
        topics = data.get("topics", [])
        for topic in topics:
            await websocket_manager.unsubscribe_from_topic(connection_id, topic)
        
        await websocket_manager.send_personal_message(
            connection_id,
            {
                "type": MessageType.NOTIFICATION.value,
                "data": {
                    "message": f"Unsubscribed from topics: {', '.join(topics)}",
                    "timestamp": websocket_manager._get_current_time()
                }
            }
        )
    
    elif message_type == "ping":
        # Respond to ping with pong
        await websocket_manager.send_personal_message(
            connection_id,
            {
                "type": "pong",
                "data": {
                    "timestamp": websocket_manager._get_current_time()
                }
            }
        )
    
    elif message_type == "get_status":
        # Send connection status
        connection = websocket_manager.active_connections.get(connection_id)
        if connection:
            await websocket_manager.send_personal_message(
                connection_id,
                {
                    "type": MessageType.STATUS_UPDATE.value,
                    "data": {
                        "connection_id": connection_id,
                        "user_id": connection.user_id,
                        "username": connection.username,
                        "connected_at": connection.connected_at.isoformat(),
                        "subscriptions": list(connection.subscriptions),
                        "timestamp": websocket_manager._get_current_time()
                    }
                }
            )
    
    else:
        # Unknown message type
        await websocket_manager.send_personal_message(
            connection_id,
            {
                "type": MessageType.ERROR.value,
                "data": {
                    "message": f"Unknown message type: {message_type}",
                    "timestamp": websocket_manager._get_current_time()
                }
            }
        )


@router.get("/connections")
async def get_active_connections(
    current_user: User = Depends(get_current_user)
):
    """Get information about active WebSocket connections (admin only)."""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    connections = []
    for connection_id, connection in websocket_manager.active_connections.items():
        connections.append({
            "connection_id": connection_id,
            "user_id": connection.user_id,
            "username": connection.username,
            "connected_at": connection.connected_at.isoformat(),
            "subscriptions": list(connection.subscriptions),
            "last_activity": connection.last_activity.isoformat() if connection.last_activity else None
        })
    
    return {
        "active_connections": connections,
        "total_connections": len(connections),
        "total_connection_count": websocket_manager.connection_count
    }


@router.post("/broadcast")
async def broadcast_message(
    message: Dict[str, Any],
    topic: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Broadcast a message to all connected clients or specific topic (admin only)."""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if topic:
        await websocket_manager.broadcast_to_topic(topic, message)
        return {"message": f"Message broadcasted to topic: {topic}"}
    else:
        await websocket_manager.broadcast_message(message)
        return {"message": "Message broadcasted to all connections"}


@router.post("/send/{user_id}")
async def send_personal_message(
    user_id: str,
    message: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Send a personal message to a specific user (admin only)."""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Find connection by user_id
    connection_id = None
    for conn_id, connection in websocket_manager.active_connections.items():
        if connection.user_id == user_id:
            connection_id = conn_id
            break
    
    if not connection_id:
        raise HTTPException(status_code=404, detail="User not connected")
    
    await websocket_manager.send_personal_message(connection_id, message)
    return {"message": f"Message sent to user: {user_id}"}


@router.delete("/connections/{connection_id}")
async def disconnect_user(
    connection_id: str,
    current_user: User = Depends(get_current_user)
):
    """Disconnect a specific WebSocket connection (admin only)."""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if connection_id not in websocket_manager.active_connections:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    await websocket_manager.disconnect(connection_id)
    return {"message": f"Connection {connection_id} disconnected"}


@router.get("/topics")
async def get_available_topics(
    current_user: User = Depends(get_current_user)
):
    """Get list of available subscription topics."""
    
    topics = [
        {
            "name": "olt_status",
            "description": "OLT status updates and alerts"
        },
        {
            "name": "ont_status", 
            "description": "ONT status updates and alerts"
        },
        {
            "name": "performance_data",
            "description": "Real-time performance metrics"
        },
        {
            "name": "alarms",
            "description": "System alarms and notifications"
        },
        {
            "name": "system_notifications",
            "description": "General system notifications"
        }
    ]
    
    return {"topics": topics}