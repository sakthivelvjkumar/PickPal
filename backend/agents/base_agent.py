import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

class EventType(Enum):
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    REPLAN_REQUIRED = "replan_required"
    DATA_DISCOVERED = "data_discovered"
    VERIFICATION_FAILED = "verification_failed"

@dataclass
class AgentEvent:
    event_id: str
    agent_id: str
    event_type: EventType
    data: Dict[str, Any]
    timestamp: datetime
    correlation_id: Optional[str] = None

class EventBus:
    def __init__(self):
        self.subscribers: Dict[EventType, List[callable]] = {}
        self.events: List[AgentEvent] = []
    
    def subscribe(self, event_type: EventType, callback: callable):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
    
    async def publish(self, event: AgentEvent):
        self.events.append(event)
        if event.event_type in self.subscribers:
            for callback in self.subscribers[event.event_type]:
                try:
                    await callback(event)
                except Exception as e:
                    logging.error(f"Event handler error: {e}")

class BaseAgent(ABC):
    def __init__(self, agent_id: str, event_bus: EventBus):
        self.agent_id = agent_id
        self.event_bus = event_bus
        self.logger = logging.getLogger(f"agent.{agent_id}")
        self.state = "idle"
        self.tasks_completed = []
    
    async def emit_event(self, event_type: EventType, data: Dict[str, Any], correlation_id: Optional[str] = None):
        event = AgentEvent(
            event_id=str(uuid.uuid4()),
            agent_id=self.agent_id,
            event_type=event_type,
            data=data,
            timestamp=datetime.now(),
            correlation_id=correlation_id
        )
        await self.event_bus.publish(event)
    
    @abstractmethod
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent-specific task"""
        pass
    
    async def handle_event(self, event: AgentEvent):
        """Handle incoming events from other agents"""
        pass
