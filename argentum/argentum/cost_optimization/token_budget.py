"""
Token budget management for preventing cost overruns.

Provides hard limits, tracking, and alerts to prevent exceeding token budgets
in multi-agent systems.
"""

from typing import Dict, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import threading
# Import ArgentumError - handle package structure flexibly
try:
    from argentum.exceptions import ArgentumError
except ImportError:
    try:
        import sys as _sys
        import os as _os
        # Get the project root (2 levels up from this file)
        _current_dir = _os.path.dirname(_os.path.abspath(__file__))
        _project_root = _os.path.dirname(_os.path.dirname(_current_dir))
        _exceptions_file = _os.path.join(_project_root, 'exceptions.py')
        if _os.path.exists(_exceptions_file):
            if _project_root not in _sys.path:
                _sys.path.insert(0, _project_root)
            from exceptions import ArgentumError
        else:
            raise ImportError("exceptions.py not found")
    except ImportError:
        # Fallback: define base exception
        class ArgentumError(Exception):
            """Base exception for Argentum."""
            def __init__(self, message: str, details: dict = None):
                self.message = message
                self.details = details or {}
                super().__init__(message)


class BudgetExceededError(ArgentumError):
    """Raised when token budget is exceeded."""
    pass


class BudgetStatus(Enum):
    """Budget status indicators."""
    OK = "ok"
    WARNING = "warning"  # Approaching limit
    CRITICAL = "critical"  # Very close to limit
    EXCEEDED = "exceeded"  # Budget exceeded


@dataclass
class BudgetAlert:
    """Budget alert information."""
    timestamp: datetime
    agent_id: Optional[str]
    status: BudgetStatus
    current_usage: int
    budget_limit: int
    usage_percentage: float
    message: str


@dataclass
class BudgetInfo:
    """Budget information snapshot."""
    total_budget: int
    current_usage: int
    remaining: int
    usage_percentage: float
    status: BudgetStatus
    per_agent_usage: Dict[str, int]
    alerts: List[BudgetAlert] = field(default_factory=list)


class TokenBudgetManager:
    """
    Manages token budgets with hard limits and tracking.
    
    Provides per-agent and global budget management with automatic
    enforcement, alerts, and rollover policies.
    """
    
    def __init__(
        self,
        total_budget: int,
        per_agent_budget: Optional[int] = None,
        alert_threshold: float = 0.8,
        critical_threshold: float = 0.95,
        on_alert: Optional[Callable[[BudgetAlert], None]] = None,
        enable_rollover: bool = False,
        rollover_percentage: float = 0.1
    ):
        """Initialize token budget manager."""
        if total_budget <= 0:
            raise ValueError("total_budget must be positive")
        if not 0 <= alert_threshold <= 1:
            raise ValueError("alert_threshold must be between 0 and 1")
        if not 0 <= critical_threshold <= 1:
            raise ValueError("critical_threshold must be between 0 and 1")
        if alert_threshold >= critical_threshold:
            raise ValueError("alert_threshold must be less than critical_threshold")
        
        self.total_budget = total_budget
        self.per_agent_budget = per_agent_budget
        self.alert_threshold = alert_threshold
        self.critical_threshold = critical_threshold
        self.on_alert = on_alert
        self.enable_rollover = enable_rollover
        self.rollover_percentage = rollover_percentage
        
        self._current_usage = 0
        self._per_agent_usage: Dict[str, int] = {}
        self._alerts: List[BudgetAlert] = []
        self._lock = threading.Lock()
        self._alerted_statuses: set = set()
    
    def can_afford(self, tokens: int, agent_id: Optional[str] = None) -> bool:
        """Check if budget can afford the requested tokens."""
        with self._lock:
            # Check global budget
            if self._current_usage + tokens > self.total_budget:
                if self.enable_rollover:
                    max_budget = int(self.total_budget * (1 + self.rollover_percentage))
                    if self._current_usage + tokens > max_budget:
                        return False
                else:
                    return False
            
            # Check per-agent budget if specified
            if agent_id and self.per_agent_budget:
                agent_usage = self._per_agent_usage.get(agent_id, 0)
                if agent_usage + tokens > self.per_agent_budget:
                    if self.enable_rollover:
                        max_agent_budget = int(self.per_agent_budget * (1 + self.rollover_percentage))
                        if agent_usage + tokens > max_agent_budget:
                            return False
                    else:
                        return False
            
            return True
    
    def can_afford_agent(self, agent_id: str, tokens: int) -> bool:
        """Check if agent-specific budget can afford tokens."""
        return self.can_afford(tokens, agent_id=agent_id)
    
    def consume(self, tokens: int, agent_id: Optional[str] = None) -> None:
        """Consume tokens from budget."""
        if tokens < 0:
            raise ValueError("tokens must be non-negative")
        
        with self._lock:
            if not self.can_afford(tokens, agent_id):
                raise BudgetExceededError(
                    f"Budget exceeded: cannot consume {tokens} tokens. "
                    f"Current usage: {self._current_usage}/{self.total_budget}",
                    {
                        "tokens_requested": tokens,
                        "current_usage": self._current_usage,
                        "total_budget": self.total_budget,
                        "agent_id": agent_id
                    }
                )
            
            self._current_usage += tokens
            
            if agent_id:
                if agent_id not in self._per_agent_usage:
                    self._per_agent_usage[agent_id] = 0
                self._per_agent_usage[agent_id] += tokens
            
            self._check_alerts(agent_id)
    
    def refund(self, tokens: int, agent_id: Optional[str] = None) -> None:
        """Refund tokens to budget."""
        if tokens < 0:
            raise ValueError("tokens must be non-negative")
        
        with self._lock:
            self._current_usage = max(0, self._current_usage - tokens)
            
            if agent_id and agent_id in self._per_agent_usage:
                self._per_agent_usage[agent_id] = max(
                    0, 
                    self._per_agent_usage[agent_id] - tokens
                )
    
    def get_status(self) -> BudgetInfo:
        """Get current budget status."""
        with self._lock:
            usage_pct = self._current_usage / self.total_budget if self.total_budget > 0 else 0
            
            if usage_pct >= 1.0:
                status = BudgetStatus.EXCEEDED
            elif usage_pct >= self.critical_threshold:
                status = BudgetStatus.CRITICAL
            elif usage_pct >= self.alert_threshold:
                status = BudgetStatus.WARNING
            else:
                status = BudgetStatus.OK
            
            return BudgetInfo(
                total_budget=self.total_budget,
                current_usage=self._current_usage,
                remaining=self.total_budget - self._current_usage,
                usage_percentage=usage_pct,
                status=status,
                per_agent_usage=self._per_agent_usage.copy(),
                alerts=self._alerts.copy()
            )
    
    def get_agent_usage(self, agent_id: str) -> int:
        """Get token usage for a specific agent."""
        with self._lock:
            return self._per_agent_usage.get(agent_id, 0)
    
    def reset(self, agent_id: Optional[str] = None) -> None:
        """Reset budget usage."""
        with self._lock:
            if agent_id:
                if agent_id in self._per_agent_usage:
                    refunded = self._per_agent_usage[agent_id]
                    self._current_usage -= refunded
                    del self._per_agent_usage[agent_id]
            else:
                self._current_usage = 0
                self._per_agent_usage.clear()
                self._alerts.clear()
                self._alerted_statuses.clear()
    
    def _check_alerts(self, agent_id: Optional[str] = None) -> None:
        """Check if alerts should be triggered."""
        usage_pct = self._current_usage / self.total_budget if self.total_budget > 0 else 0
        
        if usage_pct >= 1.0:
            status = BudgetStatus.EXCEEDED
        elif usage_pct >= self.critical_threshold:
            status = BudgetStatus.CRITICAL
        elif usage_pct >= self.alert_threshold:
            status = BudgetStatus.WARNING
        else:
            status = BudgetStatus.OK
        
        if status != BudgetStatus.OK and status not in self._alerted_statuses:
            self._alerted_statuses.add(status)
            
            alert = BudgetAlert(
                timestamp=datetime.utcnow(),
                agent_id=agent_id,
                status=status,
                current_usage=self._current_usage,
                budget_limit=self.total_budget,
                usage_percentage=usage_pct,
                message=self._get_alert_message(status, usage_pct)
            )
            
            self._alerts.append(alert)
            
            if self.on_alert:
                try:
                    self.on_alert(alert)
                except Exception:
                    pass
    
    def _get_alert_message(self, status: BudgetStatus, usage_pct: float) -> str:
        """Generate alert message."""
        if status == BudgetStatus.EXCEEDED:
            return f"Budget exceeded! Usage: {usage_pct:.1%}"
        elif status == BudgetStatus.CRITICAL:
            return f"Critical: Budget usage at {usage_pct:.1%}"
        elif status == BudgetStatus.WARNING:
            return f"Warning: Budget usage at {usage_pct:.1%}"
        else:
            return f"Budget usage: {usage_pct:.1%}"

