"""
Track and analyze changes in agent state for debugging and monitoring.

This module helps developers understand how agent state evolves during execution,
making it easier to debug unexpected behavior, optimize performance, and ensure
state consistency.

Real-world debugging scenario:
    An AI agent is tasked with researching a topic and writing a summary. The agent
    starts with empty memory, searches for information, stores facts, and updates
    its goals. When the final summary is incomplete, developers use StateDiff to
    trace exactly what changed at each step:
    
    - After search: memory gained 5 facts, tools_used increased to 3
    - After analysis: goals shifted from "gather info" to "synthesize"
    - After writing: confidence dropped, indicating insufficient information
    
    This reveals the agent didn't gather enough facts before switching to synthesis.

Example:
    >>> diff = StateDiff()
    >>> diff.snapshot("start", {"memory": ["fact1"], "tools_used": 0})
    >>> # ... agent processes ...
    >>> diff.snapshot("after_search", {"memory": ["fact1", "fact2"], "tools_used": 1})
    >>> changes = diff.get_changes("start", "after_search")
    >>> # {'memory': {'added': ['fact2']}, 'tools_used': {'from': 0, 'to': 1}}

Diff Format:
    - Added keys: {"new_key": {"added": value}}
    - Removed keys: {"old_key": {"removed": value}}
    - Changed values: {"key": {"from": old_value, "to": new_value}}
    - List changes: {"list_key": {"added": [...], "removed": [...]}}
"""

from typing import Dict, List, Any, Optional
import copy
from datetime import datetime
from .exceptions import StateDiffError, SnapshotNotFoundError, InvalidStateError
from .security import secure_state_diff

# Import cost tracking if available
try:
    from .argentum.cost_optimization.cost_tracker import CostTracker
    from .argentum.cost_optimization.token_counter import TokenCounter
    COST_TRACKING_AVAILABLE = True
except ImportError:
    COST_TRACKING_AVAILABLE = False


class StateDiff:
    """
    Track and compute differences between agent states for debugging.
    
    This class maintains labeled snapshots of agent state and computes
    developer-friendly diffs between any two snapshots. Particularly useful
    for debugging multi-step agent executions where understanding state
    evolution is crucial for identifying issues.
    
    The diff format is designed to be immediately actionable:
    - Simple value changes show old → new
    - List changes show exactly what was added/removed
    - Nested structures are flattened with dot notation
    - Missing data is clearly marked as added/removed
    
    Examples:
        Basic usage with simple state:
        >>> diff = StateDiff()
        >>> diff.snapshot("init", {"counter": 0, "active": True})
        >>> diff.snapshot("processed", {"counter": 5, "active": False})
        >>> changes = diff.get_changes("init", "processed")
        >>> # {'counter': {'from': 0, 'to': 5}, 'active': {'from': True, 'to': False}}
        
        Complex agent state with memory and tools:
        >>> initial_state = {
        ...     "memory": {
        ...         "facts": ["The sky is blue"],
        ...         "confidence": {"sky_color": 0.9}
        ...     },
        ...     "goals": ["learn_colors", "write_summary"],
        ...     "tools_used": {"search": 1, "analyze": 0},
        ...     "context": "color_research"
        ... }
        >>> diff.snapshot("research_start", initial_state)
        >>> 
        >>> after_search_state = {
        ...     "memory": {
        ...         "facts": ["The sky is blue", "Grass is green", "Sun is yellow"],
        ...         "confidence": {"sky_color": 0.9, "grass_color": 0.8}
        ...     },
        ...     "goals": ["write_summary"],  # learn_colors completed
        ...     "tools_used": {"search": 3, "analyze": 1},
        ...     "context": "color_research"
        ... }
        >>> diff.snapshot("after_search", after_search_state)
        >>> changes = diff.get_changes("research_start", "after_search")
        >>> # {
        >>> #   'memory.facts': {'added': ['Grass is green', 'Sun is yellow']},
        >>> #   'memory.confidence.grass_color': {'added': 0.8},
        >>> #   'goals': {'removed': ['learn_colors']},
        >>> #   'tools_used.search': {'from': 1, 'to': 3},
        >>> #   'tools_used.analyze': {'from': 0, 'to': 1}
        >>> # }
    """
    
    def __init__(self, track_costs: bool = False):
        """
        Initialize an empty StateDiff tracker.
        
        Args:
            track_costs: Enable cost tracking and attribution for state changes
        """
        self._snapshots: Dict[str, Dict[str, Any]] = {}
        self._sequence: List[str] = []
        self._track_costs = track_costs
        self._cost_data: Dict[str, Dict[str, Any]] = {}
        
        # Initialize cost tracker if available and enabled
        if track_costs and COST_TRACKING_AVAILABLE:
            self._cost_tracker = CostTracker()
            self._token_counter = TokenCounter()
        else:
            self._cost_tracker = None
            self._token_counter = None
    
    @property
    def snapshots(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all snapshots (read-only).
        
        Returns:
            Dictionary of all snapshots by label
        """
        return self._snapshots.copy()
    
    def snapshot(self, label: str, state: Dict[str, Any], cost_context: Optional[Dict[str, Any]] = None) -> None:
        """
        Capture a state snapshot with a descriptive label.
        
        Args:
            label: Descriptive name for this state (e.g., "after_search", "error_state")
            state: Dictionary representing the agent's current state
            cost_context: Optional cost information for this state change
                         (e.g., {"operation": "search", "tokens_used": 1500, "cost": 0.003})
            
        Raises:
            SecurityError: If input fails security validation
            
        Examples:
            >>> diff = StateDiff()
            >>> # Capture initial agent state
            >>> diff.snapshot("initialization", {
            ...     "memory": [],
            ...     "current_task": "research_topic",
            ...     "tool_calls": 0,
            ...     "confidence": 0.0
            ... })
            >>> 
            >>> # Capture state after first tool use
            >>> diff.snapshot("post_search", {
            ...     "memory": ["fact1", "fact2"],
            ...     "current_task": "research_topic",
            ...     "tool_calls": 1,
            ...     "confidence": 0.6
            ... })
        """
        # Security validation
        secure_state_diff(state, label)
        
        # Deep copy to prevent external modifications affecting stored state
        self._snapshots[label] = copy.deepcopy(state)
        if label not in self._sequence:
            self._sequence.append(label)
        
        # Track cost information if enabled
        if self._track_costs and cost_context:
            self._cost_data[label] = {
                'timestamp': datetime.now(),
                'operation': cost_context.get('operation', 'unknown'),
                'tokens_used': cost_context.get('tokens_used', 0),
                'estimated_cost': cost_context.get('cost', 0.0),
                **cost_context  # Include any additional cost metadata
            }
            
            # Record cost event in tracker if available
            if self._cost_tracker and 'tokens_used' in cost_context:
                self._cost_tracker.record_usage(
                    operation=cost_context.get('operation', 'state_change'),
                    tokens_used=cost_context['tokens_used'],
                    agent_id=cost_context.get('agent_id', 'unknown'),
                    model=cost_context.get('model', 'unknown')
                )
    
    def get_changes(self, from_label: str, to_label: str) -> Dict[str, Any]:
        """
        Compute differences between two labeled snapshots.
        
        Args:
            from_label: Starting state snapshot label
            to_label: Ending state snapshot label
            
        Returns:
            Dictionary with diff information in developer-friendly format
            
        Raises:
            KeyError: If either label doesn't exist in snapshots
            
        Examples:
            >>> diff = StateDiff()
            >>> diff.snapshot("start", {"goals": ["task1"], "progress": 0})
            >>> diff.snapshot("middle", {"goals": ["task1", "task2"], "progress": 50})
            >>> changes = diff.get_changes("start", "middle")
            >>> # {'goals': {'added': ['task2']}, 'progress': {'from': 0, 'to': 50}}
            
            Complex nested example:
            >>> diff.snapshot("before", {
            ...     "agent": {
            ...         "memory": {"facts": [1, 2], "meta": {"source": "search"}},
            ...         "state": "thinking"
            ...     }
            ... })
            >>> diff.snapshot("after", {
            ...     "agent": {
            ...         "memory": {"facts": [1, 2, 3], "meta": {"source": "analysis", "confidence": 0.9}},
            ...         "state": "acting"
            ...     }
            ... })
            >>> changes = diff.get_changes("before", "after")
            >>> # {
            >>> #   'agent.memory.facts': {'added': [3]},
            >>> #   'agent.memory.meta.source': {'from': 'search', 'to': 'analysis'},
            >>> #   'agent.memory.meta.confidence': {'added': 0.9},
            >>> #   'agent.state': {'from': 'thinking', 'to': 'acting'}
            >>> # }
        """
        if from_label not in self._snapshots:
            raise KeyError(f"Snapshot '{from_label}' not found")
        if to_label not in self._snapshots:
            raise KeyError(f"Snapshot '{to_label}' not found")
            
        from_state = self._snapshots[from_label]
        to_state = self._snapshots[to_label]
        
        diff_result = self._compute_diff(from_state, to_state)
        
        # Add cost impact analysis if cost tracking is enabled
        if self._track_costs:
            cost_impact = self._compute_cost_impact(from_label, to_label)
            if cost_impact:
                diff_result['cost_impact'] = cost_impact
        
        return diff_result
    
    def get_sequence_changes(self) -> List[Dict[str, Any]]:
        """
        Get changes across all snapshots in chronological sequence.
        
        Returns:
            List of change dictionaries, each with 'from', 'to', and 'changes' keys
            
        Examples:
            >>> diff = StateDiff()
            >>> diff.snapshot("step1", {"value": 1})
            >>> diff.snapshot("step2", {"value": 2}) 
            >>> diff.snapshot("step3", {"value": 2, "new_field": "data"})
            >>> sequence = diff.get_sequence_changes()
            >>> # [
            >>> #   {
            >>> #     'from': 'step1', 'to': 'step2',
            >>> #     'changes': {'value': {'from': 1, 'to': 2}}
            >>> #   },
            >>> #   {
            >>> #     'from': 'step2', 'to': 'step3', 
            >>> #     'changes': {'new_field': {'added': 'data'}}
            >>> #   }
            >>> # ]
            
            Use case - tracking agent decision making:
            >>> # Agent processes a user request through multiple reasoning steps
            >>> for i, (from_step, to_step) in enumerate(zip(sequence[:-1], sequence[1:])):
            ...     step_changes = sequence[i]['changes']
            ...     if 'confidence' in step_changes:
            ...         print(f"Confidence changed: {step_changes['confidence']}")
            ...     if 'current_strategy' in step_changes:
            ...         print(f"Strategy shift: {step_changes['current_strategy']}")
        """
        changes_sequence = []
        
        for i in range(len(self._sequence) - 1):
            from_label = self._sequence[i]
            to_label = self._sequence[i + 1]
            
            changes = self.get_changes(from_label, to_label)
            changes_sequence.append({
                'from': from_label,
                'to': to_label,
                'changes': changes
            })
        
        return changes_sequence
    
    def clear(self) -> None:
        """
        Reset all snapshots and sequence tracking.
        
        Examples:
            >>> diff = StateDiff()
            >>> diff.snapshot("test", {"data": 1})
            >>> len(diff._snapshots)  # 1
            >>> diff.clear()
            >>> len(diff._snapshots)  # 0
        """
        self._snapshots.clear()
        self._sequence.clear()
    
    def _compute_diff(self, old_state: Dict[str, Any], new_state: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """
        Recursively compute differences between two state dictionaries.
        
        Args:
            old_state: Original state dictionary
            new_state: Updated state dictionary  
            prefix: Key prefix for nested structures (internal use)
            
        Returns:
            Flattened difference dictionary with dot notation for nested keys
        """
        changes = {}
        
        # Get all unique keys from both states
        all_keys = set(old_state.keys()) | set(new_state.keys())
        
        for key in all_keys:
            full_key = f"{prefix}.{key}" if prefix else key
            
            old_value = old_state.get(key)
            new_value = new_state.get(key)
            
            if key not in old_state:
                # Key was added
                changes[full_key] = {"added": new_value}
            elif key not in new_state:
                # Key was removed
                changes[full_key] = {"removed": old_value}
            elif old_value != new_value:
                # Key value changed
                if isinstance(old_value, dict) and isinstance(new_value, dict):
                    # Recursively diff nested dictionaries
                    nested_changes = self._compute_diff(old_value, new_value, full_key)
                    changes.update(nested_changes)
                elif isinstance(old_value, list) and isinstance(new_value, list):
                    # Handle list differences
                    list_diff = self._compute_list_diff(old_value, new_value)
                    if list_diff:
                        changes[full_key] = list_diff
                else:
                    # Simple value change
                    changes[full_key] = {"from": old_value, "to": new_value}
        
        return changes
    
    def _compute_list_diff(self, old_list: List[Any], new_list: List[Any]) -> Optional[Dict[str, List[Any]]]:
        """
        Compute added and removed items in lists.
        
        Args:
            old_list: Original list
            new_list: Updated list
            
        Returns:
            Dictionary with 'added' and 'removed' keys, or None if no changes
        """
        old_set = set(old_list)
        new_set = set(new_list)
        
        added = [item for item in new_list if item not in old_set]
        removed = [item for item in old_list if item not in new_set]
        
        if added or removed:
            diff = {}
            if added:
                diff["added"] = added
            if removed:
                diff["removed"] = removed
            return diff
        
        return None
    
    def _compute_cost_impact(self, from_label: str, to_label: str) -> Optional[Dict[str, Any]]:
        """
        Compute cost impact between two snapshots.
        
        Args:
            from_label: Starting snapshot label
            to_label: Ending snapshot label
            
        Returns:
            Dictionary with cost impact information or None if no cost data
        """
        from_cost = self._cost_data.get(from_label, {})
        to_cost = self._cost_data.get(to_label, {})
        
        if not to_cost:
            return None
            
        cost_impact = {}
        
        # Calculate token and cost differences
        if 'tokens_used' in to_cost:
            from_tokens = from_cost.get('tokens_used', 0)
            to_tokens = to_cost['tokens_used']
            cost_impact['tokens_used'] = to_tokens - from_tokens
        
        if 'estimated_cost' in to_cost:
            from_estimated = from_cost.get('estimated_cost', 0.0)
            to_estimated = to_cost['estimated_cost']
            cost_impact['estimated_cost'] = to_estimated - from_estimated
            
        # Include operation information
        if 'operation' in to_cost:
            cost_impact['operation'] = to_cost['operation']
            
        # Calculate time elapsed
        if 'timestamp' in to_cost:
            from_time = from_cost.get('timestamp')
            to_time = to_cost['timestamp']
            if from_time:
                elapsed = (to_time - from_time).total_seconds()
                cost_impact['elapsed_seconds'] = elapsed
                
        return cost_impact if cost_impact else None
    
    def get_cost_report(self) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive cost report for all tracked snapshots.
        
        Returns:
            Dictionary with cost analysis or None if cost tracking disabled
        """
        if not self._track_costs or not self._cost_data:
            return None
            
        total_tokens = sum(cost.get('tokens_used', 0) for cost in self._cost_data.values())
        total_cost = sum(cost.get('estimated_cost', 0.0) for cost in self._cost_data.values())
        
        operations = {}
        for label, cost_data in self._cost_data.items():
            op = cost_data.get('operation', 'unknown')
            if op not in operations:
                operations[op] = {'count': 0, 'tokens': 0, 'cost': 0.0}
            operations[op]['count'] += 1
            operations[op]['tokens'] += cost_data.get('tokens_used', 0)
            operations[op]['cost'] += cost_data.get('estimated_cost', 0.0)
        
        return {
            'total_tokens': total_tokens,
            'total_cost': total_cost,
            'operation_breakdown': operations,
            'snapshot_count': len(self._cost_data),
            'cost_per_snapshot': total_cost / len(self._cost_data) if self._cost_data else 0.0
        }