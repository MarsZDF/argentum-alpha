"""
Manages temporal decay of context items in agent memory.

This module helps agents prioritize recent and important information while gradually
forgetting older, less relevant context to optimize token usage and maintain focus
on current objectives.

Use Cases:
    - Chat conversations: User preferences fade over time while recent tasks stay prominent
    - Task-oriented dialogue: Completed subtasks decay while current goals remain active
    - Multi-step reasoning: Early hypothesis fade as new evidence emerges
    - Agent debugging: Track which context influenced recent decisions

Example:
    >>> decay = ContextDecay(half_life_steps=10)
    >>> decay.add("user_name", "Alice", importance=0.9)
    >>> decay.add("task", "write email", importance=1.0)
    >>> decay.step()  # Advance time
    >>> active = decay.get_active(threshold=0.5)
    >>> # Returns items with weight > 0.5

Mathematical Model:
    weight = importance * (0.5 ^ (steps_elapsed / half_life))
    
    Where:
    - importance: Initial relevance score (0.0-1.0)
    - steps_elapsed: Time steps since item was added
    - half_life: Steps required for weight to decay to 50% of importance
"""

import math
from typing import Any, Dict, List, Tuple, Callable, Optional
from datetime import datetime

# Import cost tracking if available
try:
    from .argentum.cost_optimization.cost_tracker import CostTracker
    from .argentum.cost_optimization.token_counter import TokenCounter
    COST_TRACKING_AVAILABLE = True
except ImportError:
    COST_TRACKING_AVAILABLE = False


class ContextDecay:
    """
    Implements temporal decay for agent context management.
    
    This class tracks context items with associated importance scores and applies
    decay functions over time. Items naturally fade in relevance, allowing agents
    to focus computational resources on recent and important information.
    
    The default exponential decay model follows:
        current_weight = importance * (0.5 ^ (steps_elapsed / half_life_steps))
    
    This ensures that after 'half_life_steps' time steps, an item retains 50% of
    its original importance, creating smooth degradation over time.
    
    Attributes:
        half_life_steps: Number of steps for item to decay to 50% importance
        current_step: Current time step counter
        
    Examples:
        Basic usage with exponential decay:
        >>> decay = ContextDecay(half_life_steps=5)
        >>> decay.add("user_preference", "casual_tone", importance=0.8)
        >>> decay.add("current_task", "write_report", importance=1.0)
        >>> 
        >>> # After 5 steps, user_preference will have weight ~0.4
        >>> for _ in range(5):
        ...     decay.step()
        >>> active = decay.get_active(threshold=0.5)
        >>> # Only current_task remains above threshold
        
        Custom decay function:
        >>> def linear_decay(importance, steps, half_life):
        ...     return max(0, importance - (steps / half_life) * 0.5 * importance)
        >>> 
        >>> decay = ContextDecay(half_life_steps=10, decay_function=linear_decay)
    """
    
    def __init__(self, half_life_steps: int, decay_function: Optional[Callable[[float, int, int], float]] = None,
                 cost_optimization: bool = False, max_context_cost: float = 1.0):
        """
        Initialize context decay manager.
        
        Args:
            half_life_steps: Number of steps for items to decay to 50% of original importance
            decay_function: Optional custom decay function. Defaults to exponential decay.
                           Function signature: (importance, steps_elapsed, half_life) -> current_weight
            cost_optimization: Enable cost-based context management and pruning
            max_context_cost: Maximum cost allowed for context storage (in dollars)
        
        Raises:
            ValueError: If half_life_steps <= 0
            
        Examples:
            >>> decay = ContextDecay(half_life_steps=20)
            >>> # User preferences fade over 20 interactions
            
            >>> def custom_decay(imp, steps, half_life):
            ...     return imp * math.exp(-steps / half_life)
            >>> decay = ContextDecay(10, custom_decay)
        """
        if half_life_steps <= 0:
            raise ValueError("half_life_steps must be positive")
            
        self.half_life_steps = half_life_steps
        self.current_step = 0
        self._items: Dict[str, Dict[str, Any]] = {}
        
        # Cost optimization settings
        self._cost_optimization = cost_optimization
        self._max_context_cost = max_context_cost
        self._current_cost = 0.0
        self._cost_history: List[Dict[str, Any]] = []
        
        # Initialize cost tracker if available and enabled
        if cost_optimization and COST_TRACKING_AVAILABLE:
            self._cost_tracker = CostTracker()
            self._token_counter = TokenCounter()
        else:
            self._cost_tracker = None
            self._token_counter = None
        
        if decay_function is None:
            self._decay_function = self._exponential_decay
        else:
            self._decay_function = decay_function
    
    def add(self, key: str, value: Any, importance: float = 1.0, timestamp: Optional[int] = None, 
            storage_cost: float = 0.0) -> None:
        """
        Add or update a context item with importance score.
        
        Args:
            key: Unique identifier for the context item
            value: The context data to store
            importance: Initial importance score (0.0-1.0, default: 1.0)
            timestamp: Optional step when item was added (default: current_step)
            storage_cost: Cost to store this context item (used for cost optimization)
        
        Raises:
            ValueError: If importance not in range [0.0, 1.0]
            
        Examples:
            >>> decay = ContextDecay(half_life_steps=15)
            >>> decay.add("user_name", "Bob", importance=0.7)
            >>> decay.add("urgent_task", "fix_bug", importance=1.0)
            >>> 
            >>> # Update existing item (resets its timestamp)
            >>> decay.add("user_name", "Robert", importance=0.8)
        """
        if not 0.0 <= importance <= 1.0:
            raise ValueError(f"Importance must be between 0.0 and 1.0, got {importance}")
            
        if timestamp is None:
            timestamp = self.current_step
            
        # Check cost constraints if cost optimization is enabled
        if self._cost_optimization and storage_cost > 0:
            # Check if adding this item would exceed budget
            if self._current_cost + storage_cost > self._max_context_cost:
                self._prune_by_cost_effectiveness()
                
            # If still over budget after pruning, try cost-based importance adjustment
            if self._current_cost + storage_cost > self._max_context_cost:
                # Adjust importance based on cost efficiency
                cost_efficiency = importance / max(storage_cost, 0.001)  # Avoid division by zero
                adjusted_importance = min(importance, cost_efficiency * 0.1)
                importance = max(0.1, adjusted_importance)  # Minimum viable importance
        
        # Remove existing item cost if updating
        if key in self._items and self._cost_optimization:
            self._current_cost -= self._items[key].get('storage_cost', 0.0)
        
        self._items[key] = {
            'value': value,
            'importance': importance,
            'added_at': timestamp,
            'storage_cost': storage_cost,
            'cost_effectiveness': importance / max(storage_cost, 0.001) if storage_cost > 0 else importance
        }
        
        # Update current cost
        if self._cost_optimization:
            self._current_cost += storage_cost
            
            # Record cost event
            if self._cost_tracker:
                self._cost_tracker.record_usage(
                    operation='context_storage',
                    tokens_used=int(storage_cost * 1000),  # Rough conversion
                    agent_id='context_manager',
                    model='storage'
                )
    
    def step(self) -> None:
        """
        Advance time by one step, causing all items to decay.
        
        This method should be called regularly (e.g., after each user interaction
        or agent reasoning cycle) to maintain accurate temporal relationships.
        
        Examples:
            >>> decay = ContextDecay(half_life_steps=10)
            >>> decay.add("info", "data", importance=1.0)
            >>> 
            >>> decay.step()  # Time advances
            >>> decay.step()  # Time advances again
            >>> 
            >>> # Item now has weight = 1.0 * (0.5 ^ (2/10)) ≈ 0.87
        """
        self.current_step += 1
    
    def get_active(self, threshold: float = 0.3) -> List[Tuple[str, Any, float]]:
        """
        Return context items with current weight above threshold.
        
        Args:
            threshold: Minimum weight for items to be considered active (0.0-1.0)
            
        Returns:
            List of tuples: (key, value, current_weight) for items above threshold,
            sorted by current weight in descending order
            
        Examples:
            >>> decay = ContextDecay(half_life_steps=5)
            >>> decay.add("recent", "important_data", importance=1.0)
            >>> decay.add("old", "stale_data", importance=0.5)
            >>> 
            >>> # After some time
            >>> for _ in range(3):
            ...     decay.step()
            >>> 
            >>> active = decay.get_active(threshold=0.4)
            >>> # Returns only items with weight > 0.4
        """
        active_items = []
        
        for key, item in self._items.items():
            current_weight = self._calculate_current_weight(item)
            if current_weight >= threshold:
                active_items.append((key, item['value'], current_weight))
        
        # Sort by weight descending (most relevant first)
        active_items.sort(key=lambda x: x[2], reverse=True)
        return active_items
    
    def get_all_items(self) -> List[Tuple[str, Any, float, float]]:
        """
        Return all context items with their current weights and importance.
        
        Returns:
            List of tuples: (key, value, current_weight, importance) for all items,
            sorted by current weight in descending order
            
        Examples:
            >>> decay = ContextDecay(half_life_steps=5)
            >>> decay.add("item1", "data1", importance=0.9)
            >>> decay.add("item2", "data2", importance=0.5)
            >>> 
            >>> all_items = decay.get_all_items()
            >>> for key, value, weight, importance in all_items:
            ...     print(f"{key}: weight={weight:.2f}, importance={importance:.2f}")
        """
        all_items = []
        
        for key, item in self._items.items():
            current_weight = self._calculate_current_weight(item)
            all_items.append((key, item['value'], current_weight, item['importance']))
        
        # Sort by weight descending (most relevant first)
        all_items.sort(key=lambda x: x[2], reverse=True)
        return all_items
    
    def clear_expired(self, threshold: float = 0.1) -> int:
        """
        Remove items with weight below threshold to free memory.
        
        Args:
            threshold: Minimum weight to retain items (default: 0.1)
            
        Returns:
            Number of items removed
            
        Examples:
            >>> decay = ContextDecay(half_life_steps=5)
            >>> decay.add("temp1", "data1", importance=0.3)
            >>> decay.add("temp2", "data2", importance=0.3)
            >>> 
            >>> # Let items decay significantly
            >>> for _ in range(20):
            ...     decay.step()
            >>> 
            >>> removed = decay.clear_expired(threshold=0.05)
            >>> # Returns number of expired items removed
        """
        to_remove = []
        
        for key, item in self._items.items():
            current_weight = self._calculate_current_weight(item)
            if current_weight < threshold:
                to_remove.append(key)
        
        for key in to_remove:
            del self._items[key]
            
        return len(to_remove)
    
    def get_stats(self) -> Dict[str, float]:
        """
        Return statistics about current context state.
        
        Returns:
            Dictionary containing:
            - total_items: Total number of stored items
            - active_items: Number of items above default threshold (0.3)
            - avg_decay: Average decay weight across all items
            - oldest_age: Age in steps of oldest item
            
        Examples:
            >>> decay = ContextDecay(half_life_steps=10)
            >>> decay.add("item1", "data1", importance=1.0)
            >>> decay.add("item2", "data2", importance=0.5)
            >>> decay.step()
            >>> 
            >>> stats = decay.get_stats()
            >>> # {'total_items': 2, 'active_items': 2, 'avg_decay': 0.87, 'oldest_age': 1}
        """
        if not self._items:
            return {
                'total_items': 0,
                'active_items': 0, 
                'avg_decay': 0.0,
                'oldest_age': 0
            }
        
        weights = []
        ages = []
        active_count = 0
        
        for item in self._items.values():
            weight = self._calculate_current_weight(item)
            age = self.current_step - item['added_at']
            
            weights.append(weight)
            ages.append(age)
            
            if weight >= 0.3:  # Default threshold
                active_count += 1
        
        return {
            'total_items': len(self._items),
            'active_items': active_count,
            'avg_decay': sum(weights) / len(weights),
            'oldest_age': max(ages) if ages else 0
        }
    
    def _calculate_current_weight(self, item: Dict[str, Any]) -> float:
        """Calculate current weight of an item based on decay function."""
        steps_elapsed = self.current_step - item['added_at']
        return self._decay_function(item['importance'], steps_elapsed, self.half_life_steps)
    
    def _exponential_decay(self, importance: float, steps_elapsed: int, half_life: int) -> float:
        """Default exponential decay function."""
        return importance * (0.5 ** (steps_elapsed / half_life))
    
    def _prune_by_cost_effectiveness(self) -> None:
        """
        Remove items with lowest cost effectiveness to free up budget.
        """
        if not self._cost_optimization or not self._items:
            return
            
        # Sort items by cost effectiveness (ascending - least effective first)
        items_by_effectiveness = sorted(
            self._items.items(),
            key=lambda x: x[1].get('cost_effectiveness', 0.0)
        )
        
        # Remove items until we're under budget or have room for new items
        target_cost = self._max_context_cost * 0.8  # Leave 20% buffer
        removed_items = []
        
        for key, item in items_by_effectiveness:
            if self._current_cost <= target_cost:
                break
                
            self._current_cost -= item.get('storage_cost', 0.0)
            removed_items.append(key)
            del self._items[key]
        
        # Record pruning event
        if removed_items and self._cost_tracker:
            self._cost_history.append({
                'timestamp': datetime.now(),
                'action': 'cost_pruning',
                'items_removed': len(removed_items),
                'cost_freed': sum(self._items.get(k, {}).get('storage_cost', 0.0) for k in removed_items)
            })
    
    def get_cost_report(self) -> Dict[str, Any]:
        """
        Get comprehensive cost report for context management.
        
        Returns:
            Dictionary with cost analysis or empty dict if cost optimization disabled
        """
        if not self._cost_optimization:
            return {"error": "Cost optimization not enabled"}
            
        total_items = len(self._items)
        if total_items == 0:
            return {
                "total_items": 0,
                "total_cost": 0.0,
                "average_cost_per_item": 0.0,
                "cost_efficiency": 0.0
            }
        
        total_importance = sum(item['importance'] for item in self._items.values())
        total_cost = self._current_cost
        items_pruned = sum(event.get('items_removed', 0) for event in self._cost_history)
        cost_saved = sum(event.get('cost_freed', 0.0) for event in self._cost_history)
        
        # Calculate cost effectiveness distribution
        effectiveness_scores = [item.get('cost_effectiveness', 0.0) for item in self._items.values()]
        avg_effectiveness = sum(effectiveness_scores) / len(effectiveness_scores) if effectiveness_scores else 0.0
        
        return {
            "total_items": total_items,
            "total_cost": total_cost,
            "max_cost_budget": self._max_context_cost,
            "budget_utilization": total_cost / self._max_context_cost,
            "average_cost_per_item": total_cost / total_items,
            "cost_efficiency": total_importance / max(total_cost, 0.001),
            "items_pruned": items_pruned,
            "cost_saved": cost_saved,
            "average_cost_effectiveness": avg_effectiveness,
            "cost_history": self._cost_history[-10:]  # Last 10 cost events
        }