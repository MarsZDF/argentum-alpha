"""
Cost tracking and attribution for AI agent operations.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import threading
from .token_counter import TokenUsage, TokenizerType, estimate_cost

@dataclass
class CostBreakdown:
    """Cost breakdown by category."""
    by_agent: Dict[str, float] = field(default_factory=dict)
    by_operation: Dict[str, float] = field(default_factory=dict)
    by_model: Dict[str, float] = field(default_factory=dict)
    by_time_period: Dict[str, float] = field(default_factory=dict)
    input_cost: float = 0.0
    output_cost: float = 0.0
    total_cost: float = 0.0

@dataclass
class CostEvent:
    """Individual cost event."""
    timestamp: datetime
    agent_id: Optional[str]
    operation: str
    model: str
    token_usage: TokenUsage
    cost: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CostReport:
    """Comprehensive cost report."""
    start_time: datetime
    end_time: datetime
    total_cost: float
    total_tokens: int
    event_count: int
    breakdown: CostBreakdown
    top_agents: List[tuple] = field(default_factory=list)
    top_operations: List[tuple] = field(default_factory=list)
    cost_trend: List[tuple] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

class CostTracker:
    """Track and analyze costs for AI agent operations."""
    
    def __init__(self, time_bucket_size: int = 3600):
        self.time_bucket_size = time_bucket_size
        self._events: List[CostEvent] = []
        self._lock = threading.Lock()
        self._start_time = datetime.utcnow()
    
    def record_usage(self, operation: str, tokens_used: int, agent_id: Optional[str] = None, 
                     model: str = "gpt-4", cost: Optional[float] = None, 
                     metadata: Optional[Dict[str, Any]] = None) -> CostEvent:
        """
        Simple interface for recording token usage.
        
        Args:
            operation: Type of operation (e.g., "completion", "embedding")
            tokens_used: Number of tokens consumed
            agent_id: ID of the agent responsible for this usage
            model: Model name used
            cost: Actual cost if known (otherwise estimated)
            metadata: Additional metadata
        """
        from .token_counter import TokenUsage, TokenizerType
        
        # Create TokenUsage object
        if model.lower().startswith("gpt-4"):
            tokenizer_type = TokenizerType.OPENAI_GPT4
        elif model.lower().startswith("gpt-3.5") or "turbo" in model.lower():
            tokenizer_type = TokenizerType.OPENAI_GPT35
        elif "claude" in model.lower():
            tokenizer_type = TokenizerType.ANTHROPIC_CLAUDE
        else:
            tokenizer_type = TokenizerType.APPROXIMATE
        
        # Estimate input/output split (80% input, 20% output typical)
        input_tokens = int(tokens_used * 0.8)
        output_tokens = tokens_used - input_tokens
        
        token_usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=tokens_used,
            tokenizer_type=tokenizer_type,
            estimated=cost is None
        )
        
        # Override cost if provided
        if cost is not None:
            # Store original cost_estimate and override
            original_cost = token_usage.cost_estimate
            token_usage.__dict__['cost_estimate'] = cost
        
        return self.record_cost(agent_id, operation, model, token_usage, metadata)
    
    def record_cost(self, agent_id: Optional[str], operation: str, model: str,
                    token_usage: TokenUsage, metadata: Optional[Dict[str, Any]] = None) -> CostEvent:
        cost = token_usage.cost_estimate
        event = CostEvent(
            timestamp=datetime.utcnow(),
            agent_id=agent_id,
            operation=operation,
            model=model,
            token_usage=token_usage,
            cost=cost,
            metadata=metadata or {}
        )
        with self._lock:
            self._events.append(event)
        return event
    
    def get_total_cost(self) -> float:
        with self._lock:
            return sum(event.cost for event in self._events)
    
    def get_cost_for_period(self, start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None) -> float:
        if start_time is None:
            start_time = self._start_time
        if end_time is None:
            end_time = datetime.utcnow()
        with self._lock:
            period_events = [e for e in self._events if start_time <= e.timestamp <= end_time]
            return sum(event.cost for event in period_events)
    
    def get_cost_by_agent(self) -> Dict[str, float]:
        with self._lock:
            by_agent = defaultdict(float)
            for event in self._events:
                agent_id = event.agent_id or "unknown"
                by_agent[agent_id] += event.cost
            return dict(by_agent)
    
    def get_cost_by_operation(self) -> Dict[str, float]:
        with self._lock:
            by_operation = defaultdict(float)
            for event in self._events:
                by_operation[event.operation] += event.cost
            return dict(by_operation)
    
    def get_cost_by_model(self) -> Dict[str, float]:
        with self._lock:
            by_model = defaultdict(float)
            for event in self._events:
                by_model[event.model] += event.cost
            return dict(by_model)
    
    def get_cost_report(self, agent_id: Optional[str] = None, start_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None) -> CostReport:
        """Get cost report with optional filtering by agent."""
        if start_time is None:
            start_time = self._start_time
        if end_time is None:
            end_time = datetime.utcnow()
        
        with self._lock:
            # Filter by agent if specified
            events = self._events
            if agent_id is not None:
                events = [e for e in events if e.agent_id == agent_id]
            
            period_events = [e for e in events if start_time <= e.timestamp <= end_time]
            if not period_events:
                return CostReport(start_time=start_time, end_time=end_time, total_cost=0.0,
                                total_tokens=0, event_count=0, breakdown=CostBreakdown())
            
            by_agent = defaultdict(float)
            by_operation = defaultdict(float)
            by_model = defaultdict(float)
            input_cost = 0.0
            output_cost = 0.0
            total_tokens = 0
            by_time = defaultdict(float)
            
            for event in period_events:
                agent_key = event.agent_id or "unknown"
                by_agent[agent_key] += event.cost
                by_operation[event.operation] += event.cost
                by_model[event.model] += event.cost
                
                # Safe token cost calculation
                try:
                    from .token_counter import estimate_cost
                    input_cost += estimate_cost(event.token_usage.input_tokens, event.token_usage.tokenizer_type, False)
                    output_cost += estimate_cost(event.token_usage.output_tokens, event.token_usage.tokenizer_type, True)
                except:
                    # Fallback if estimate_cost fails
                    input_cost += event.cost * 0.6  # Assume 60% input cost
                    output_cost += event.cost * 0.4  # Assume 40% output cost
                
                total_tokens += event.token_usage.total_tokens
                time_bucket = event.timestamp.replace(minute=0, second=0, microsecond=0).isoformat()
                by_time[time_bucket] += event.cost
            
            breakdown = CostBreakdown(
                by_agent=dict(by_agent), by_operation=dict(by_operation), by_model=dict(by_model),
                by_time_period=dict(by_time), input_cost=input_cost, output_cost=output_cost,
                total_cost=input_cost + output_cost
            )
            
            top_agents = sorted(by_agent.items(), key=lambda x: x[1], reverse=True)[:10]
            top_operations = sorted(by_operation.items(), key=lambda x: x[1], reverse=True)[:10]
            cost_trend = sorted(by_time.items())
            recommendations = self._generate_recommendations(breakdown, by_agent, by_operation, by_model)
            
            return CostReport(start_time=start_time, end_time=end_time, total_cost=breakdown.total_cost,
                            total_tokens=total_tokens, event_count=len(period_events), breakdown=breakdown,
                            top_agents=top_agents, top_operations=top_operations, cost_trend=cost_trend,
                            recommendations=recommendations)
    
    def get_report(self, start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None) -> CostReport:
        if start_time is None:
            start_time = self._start_time
        if end_time is None:
            end_time = datetime.utcnow()
        with self._lock:
            period_events = [e for e in self._events if start_time <= e.timestamp <= end_time]
            if not period_events:
                return CostReport(start_time=start_time, end_time=end_time, total_cost=0.0,
                                total_tokens=0, event_count=0, breakdown=CostBreakdown())
            by_agent = defaultdict(float)
            by_operation = defaultdict(float)
            by_model = defaultdict(float)
            input_cost = 0.0
            output_cost = 0.0
            total_tokens = 0
            by_time = defaultdict(float)
            for event in period_events:
                agent_id = event.agent_id or "unknown"
                by_agent[agent_id] += event.cost
                by_operation[event.operation] += event.cost
                by_model[event.model] += event.cost
                input_cost += estimate_cost(event.token_usage.input_tokens, event.token_usage.tokenizer_type, False)
                output_cost += estimate_cost(event.token_usage.output_tokens, event.token_usage.tokenizer_type, True)
                total_tokens += event.token_usage.total_tokens
                time_bucket = event.timestamp.replace(minute=0, second=0, microsecond=0).isoformat()
                by_time[time_bucket] += event.cost
            breakdown = CostBreakdown(
                by_agent=dict(by_agent), by_operation=dict(by_operation), by_model=dict(by_model),
                by_time_period=dict(by_time), input_cost=input_cost, output_cost=output_cost,
                total_cost=input_cost + output_cost
            )
            top_agents = sorted(by_agent.items(), key=lambda x: x[1], reverse=True)[:10]
            top_operations = sorted(by_operation.items(), key=lambda x: x[1], reverse=True)[:10]
            cost_trend = sorted(by_time.items())
            recommendations = self._generate_recommendations(breakdown, by_agent, by_operation, by_model)
            return CostReport(start_time=start_time, end_time=end_time, total_cost=breakdown.total_cost,
                            total_tokens=total_tokens, event_count=len(period_events), breakdown=breakdown,
                            top_agents=top_agents, top_operations=top_operations, cost_trend=cost_trend,
                            recommendations=recommendations)
    
    def _generate_recommendations(self, breakdown: CostBreakdown, by_agent: Dict[str, float],
                                 by_operation: Dict[str, float], by_model: Dict[str, float]) -> List[str]:
        recommendations = []
        if by_model:
            expensive_models = [m for m in by_model.keys() if "gpt-4" in m.lower() or "claude-3-opus" in m.lower()]
            if expensive_models:
                total_expensive_cost = sum(by_model[m] for m in expensive_models)
                total_cost = breakdown.total_cost
                if total_expensive_cost / total_cost > 0.5:
                    recommendations.append(f"Consider using cheaper models. Expensive models account for {total_expensive_cost/total_cost:.1%} of costs.")
        return recommendations
    
    def clear(self, before_time: Optional[datetime] = None) -> int:
        with self._lock:
            if before_time is None:
                count = len(self._events)
                self._events.clear()
                return count
            else:
                original_count = len(self._events)
                self._events = [e for e in self._events if e.timestamp >= before_time]
                return original_count - len(self._events)
    
    def export_events(self, format: str = "json") -> Any:
        import json
        import csv
        import io
        with self._lock:
            events_data = [{"timestamp": e.timestamp.isoformat(), "agent_id": e.agent_id,
                          "operation": e.operation, "model": e.model, "input_tokens": e.token_usage.input_tokens,
                          "output_tokens": e.token_usage.output_tokens, "total_tokens": e.token_usage.total_tokens,
                          "cost": e.cost, "metadata": e.metadata} for e in self._events]
            if format == "json":
                return json.dumps(events_data, indent=2)
            elif format == "csv":
                output = io.StringIO()
                if events_data:
                    writer = csv.DictWriter(output, fieldnames=events_data[0].keys())
                    writer.writeheader()
                    writer.writerows(events_data)
                return output.getvalue()
            else:
                raise ValueError(f"Unsupported format: {format}")
