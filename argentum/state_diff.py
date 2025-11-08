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
from .exceptions import StateDiffError, SnapshotNotFoundError, InvalidStateError
from .security import secure_state_diff


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
    
    def __init__(self):
        """Initialize an empty StateDiff tracker."""
        self._snapshots: Dict[str, Dict[str, Any]] = {}
        self._sequence: List[str] = []
    
    def snapshot(self, label: str, state: Dict[str, Any]) -> None:
        """
        Capture a state snapshot with a descriptive label.
        
        Args:
            label: Descriptive name for this state (e.g., "after_search", "error_state")
            state: Dictionary representing the agent's current state
            
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
        
        return self._compute_diff(from_state, to_state)
    
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