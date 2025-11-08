"""
Budget allocation across agents and tasks.
"""
from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import threading
from .token_budget import TokenBudgetManager

class AllocationStrategy(Enum):
    EQUAL = "equal"
    PRIORITY_BASED = "priority_based"
    USAGE_BASED = "usage_based"
    FAIR_SHARE = "fair_share"
    DYNAMIC = "dynamic"

@dataclass
class AgentAllocation:
    agent_id: str
    allocated_budget: int
    used_budget: int
    remaining_budget: int
    priority: int = 1
    usage_percentage: float = 0.0

@dataclass
class AllocationPlan:
    total_budget: int
    allocations: Dict[str, AgentAllocation]
    strategy: AllocationStrategy
    created_at: datetime = field(default_factory=datetime.utcnow)

class BudgetAllocator:
    def __init__(self, total_budget: int, strategy: AllocationStrategy = AllocationStrategy.EQUAL, reserve_percentage: float = 0.1):
        self.total_budget = total_budget
        self.strategy = strategy
        self.reserve_percentage = reserve_percentage
        self._agents: Dict[str, Dict] = {}
        self._allocations: Dict[str, int] = {}
        self._usage: Dict[str, int] = {}
        self._lock = threading.Lock()
    
    def register_agent(self, agent_id: str, priority: int = 1, initial_budget: Optional[int] = None):
        with self._lock:
            self._agents[agent_id] = {"priority": priority, "registered_at": datetime.utcnow()}
            self._usage[agent_id] = 0
            if initial_budget:
                self._allocations[agent_id] = initial_budget
    
    def allocate(self) -> AllocationPlan:
        with self._lock:
            available_budget = int(self.total_budget * (1 - self.reserve_percentage))
            if self.strategy == AllocationStrategy.EQUAL:
                allocations = self._equal_allocation(available_budget)
            elif self.strategy == AllocationStrategy.PRIORITY_BASED:
                allocations = self._priority_based_allocation(available_budget)
            else:
                allocations = self._equal_allocation(available_budget)
            self._allocations = allocations
            agent_allocations = {}
            for agent_id, allocated in allocations.items():
                used = self._usage.get(agent_id, 0)
                priority = self._agents.get(agent_id, {}).get("priority", 1)
                usage_pct = (used / allocated * 100) if allocated > 0 else 0.0
                agent_allocations[agent_id] = AgentAllocation(agent_id, allocated, used, allocated - used, priority, usage_pct)
            return AllocationPlan(self.total_budget, agent_allocations, self.strategy)
    
    def record_usage(self, agent_id: str, tokens: int):
        with self._lock:
            if agent_id not in self._usage:
                self._usage[agent_id] = 0
            self._usage[agent_id] += tokens
    
    def get_agent_budget(self, agent_id: str) -> Optional[int]:
        with self._lock:
            return self._allocations.get(agent_id)
    
    def _equal_allocation(self, available_budget: int) -> Dict[str, int]:
        agent_count = len(self._agents)
        if agent_count == 0:
            return {}
        per_agent = available_budget // agent_count
        return {agent_id: per_agent for agent_id in self._agents.keys()}
    
    def _priority_based_allocation(self, available_budget: int) -> Dict[str, int]:
        if not self._agents:
            return {}
        total_priority = sum(agent_info.get("priority", 1) for agent_info in self._agents.values())
        allocations = {}
        for agent_id, agent_info in self._agents.items():
            priority = agent_info.get("priority", 1)
            allocation = int(available_budget * (priority / total_priority))
            allocations[agent_id] = allocation
        return allocations
