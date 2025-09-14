import asyncio
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass
import json
import time
from .utils import logger, log_context
from .messages import Trace

@dataclass
class Message:
    topic: str
    payload: Any
    trace: Trace
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

class MessageBus:
    """Lightweight in-process pub/sub message bus with tracing."""
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._message_history: List[Message] = []
        self._max_history = 1000
    
    async def subscribe(self, topic: str, handler: Callable[[Message], Any]):
        """Subscribe to a topic with a handler function."""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        
        self._subscribers[topic].append(handler)
        logger.info(f"Subscribed to topic: {topic}")
    
    async def unsubscribe(self, topic: str, handler: Callable[[Message], Any]):
        """Unsubscribe from a topic."""
        if topic in self._subscribers and handler in self._subscribers[topic]:
            self._subscribers[topic].remove(handler)
            logger.info(f"Unsubscribed from topic: {topic}")
    
    async def publish(self, topic: str, payload: Any, trace: Trace) -> List[Any]:
        """Publish a message to a topic and return results from all handlers."""
        message = Message(topic=topic, payload=payload, trace=trace)
        
        # Store in history
        self._message_history.append(message)
        if len(self._message_history) > self._max_history:
            self._message_history.pop(0)
        
        with log_context(trace.request_id):
            logger.info(f"Publishing message to topic: {topic} from {trace.source_agent}")
        
        results = []
        if topic in self._subscribers:
            for handler in self._subscribers[topic]:
                try:
                    with log_context(trace.request_id):
                        if asyncio.iscoroutinefunction(handler):
                            result = await handler(message)
                        else:
                            result = handler(message)
                        results.append(result)
                except Exception as e:
                    with log_context(trace.request_id):
                        logger.error(f"Handler error for topic {topic}: {e}")
                    raise
        
        return results
    
    async def request_response(self, topic: str, payload: Any, trace: Trace, timeout: float = 30.0) -> Any:
        """Send a request and wait for a single response."""
        response_topic = f"{topic}_response_{trace.request_id}_{int(time.time())}"
        response_received = asyncio.Event()
        response_data = None
        
        async def response_handler(message: Message):
            nonlocal response_data
            response_data = message.payload
            response_received.set()
        
        await self.subscribe(response_topic, response_handler)
        
        try:
            # Include response topic in the request
            request_payload = {
                "data": payload,
                "response_topic": response_topic
            }
            
            await self.publish(topic, request_payload, trace)
            
            # Wait for response
            await asyncio.wait_for(response_received.wait(), timeout=timeout)
            return response_data
            
        finally:
            await self.unsubscribe(response_topic, response_handler)
    
    def get_message_history(self, request_id: Optional[str] = None, topic: Optional[str] = None) -> List[Message]:
        """Get message history, optionally filtered by request_id or topic."""
        messages = self._message_history
        
        if request_id:
            messages = [m for m in messages if m.trace.request_id == request_id]
        
        if topic:
            messages = [m for m in messages if m.topic == topic]
        
        return messages
    
    def get_trace_summary(self, request_id: str) -> Dict[str, Any]:
        """Get a summary of all messages for a request_id."""
        messages = self.get_message_history(request_id=request_id)
        
        summary = {
            "request_id": request_id,
            "total_messages": len(messages),
            "topics": list(set(m.topic for m in messages)),
            "agents": list(set(m.trace.source_agent for m in messages)),
            "timeline": [
                {
                    "timestamp": m.timestamp,
                    "topic": m.topic,
                    "agent": m.trace.source_agent,
                    "step": m.trace.step
                }
                for m in messages
            ]
        }
        
        return summary

# Global message bus instance
bus = MessageBus()

class AgentBase:
    """Base class for all agents with message bus integration."""
    
    def __init__(self, name: str):
        self.name = name
        self.bus = bus
    
    async def send_message(self, topic: str, payload: Any, trace: Trace) -> List[Any]:
        """Send a message via the bus."""
        return await self.bus.publish(topic, payload, trace)
    
    async def request(self, topic: str, payload: Any, trace: Trace, timeout: float = 30.0) -> Any:
        """Send a request and wait for response."""
        return await self.bus.request_response(topic, payload, trace, timeout)
    
    async def subscribe_to(self, topic: str, handler: Callable):
        """Subscribe to a topic."""
        await self.bus.subscribe(topic, handler)
    
    def create_trace(self, request_id: str, step: str) -> Trace:
        """Create a trace object for this agent."""
        return Trace(
            request_id=request_id,
            step=step,
            source_agent=self.name,
            ts=time.time()
        )
