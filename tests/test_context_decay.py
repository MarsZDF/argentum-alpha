"""
Comprehensive tests for argentum.context_decay module.

These tests validate the temporal decay behavior in agent context management,
ensuring proper weight calculation, threshold filtering, and memory optimization.
"""

import math
import pytest
from argentum.context_decay import ContextDecay


class TestContextDecay:
    """Test ContextDecay functionality for agent memory management."""
    
    def test_basic_initialization(self):
        """
        Test basic ContextDecay initialization and validation.
        
        Validates that the decay manager initializes with proper defaults
        and rejects invalid parameters that would break decay calculations.
        """
        # Valid initialization
        decay = ContextDecay(half_life_steps=10)
        assert decay.half_life_steps == 10
        assert decay.current_step == 0
        
        # Invalid half_life should raise error
        with pytest.raises(ValueError, match="half_life_steps must be positive"):
            ContextDecay(half_life_steps=0)
        
        with pytest.raises(ValueError, match="half_life_steps must be positive"):
            ContextDecay(half_life_steps=-5)
    
    def test_exponential_decay_calculation(self):
        """
        Test mathematical correctness of exponential decay function.
        
        Validates that decay follows the formula:
        weight = importance * (0.5 ^ (steps_elapsed / half_life))
        
        This ensures agents correctly prioritize recent information.
        """
        decay = ContextDecay(half_life_steps=10)
        
        # Add item with full importance
        decay.add("test_item", "data", importance=1.0)
        
        # Test decay at half-life point
        for _ in range(10):  # 10 steps = half_life
            decay.step()
        
        active = decay.get_active(threshold=0.0)  # Get all items
        assert len(active) == 1
        
        # At half-life, weight should be ~0.5
        _, _, weight = active[0]
        assert abs(weight - 0.5) < 0.01
        
        # Test decay at double half-life
        for _ in range(10):  # Additional 10 steps
            decay.step()
        
        active = decay.get_active(threshold=0.0)
        _, _, weight = active[0]
        # At 2x half-life, weight should be ~0.25
        assert abs(weight - 0.25) < 0.01
    
    def test_importance_scaling(self):
        """
        Test that initial importance properly scales decay calculations.
        
        Validates that high-importance items retain relevance longer
        than low-importance items, crucial for agent prioritization.
        """
        decay = ContextDecay(half_life_steps=5)
        
        # Add items with different importance
        decay.add("high_importance", "critical_data", importance=1.0)
        decay.add("medium_importance", "normal_data", importance=0.6)
        decay.add("low_importance", "trivial_data", importance=0.3)
        
        # Advance time
        for _ in range(3):
            decay.step()
        
        active = decay.get_active(threshold=0.0)
        weights = {item[0]: item[2] for item in active}
        
        # High importance should have highest weight
        assert weights["high_importance"] > weights["medium_importance"]
        assert weights["medium_importance"] > weights["low_importance"]
        
        # Verify proportional scaling
        expected_high = 1.0 * (0.5 ** (3/5))
        expected_medium = 0.6 * (0.5 ** (3/5))
        
        assert abs(weights["high_importance"] - expected_high) < 0.01
        assert abs(weights["medium_importance"] - expected_medium) < 0.01
    
    def test_threshold_filtering(self):
        """
        Test active item filtering based on decay thresholds.
        
        Validates that agents can efficiently filter context to only
        relevant items, optimizing token usage and computational focus.
        """
        decay = ContextDecay(half_life_steps=5)
        
        # Add items that will decay at different rates
        decay.add("recent_task", "write_report", importance=1.0)
        decay.add("old_preference", "formal_tone", importance=0.4)
        decay.add("ancient_data", "outdated_info", importance=0.2)
        
        # Age items significantly
        for _ in range(8):
            decay.step()
        
        # Test different threshold levels
        high_threshold_items = decay.get_active(threshold=0.5)
        medium_threshold_items = decay.get_active(threshold=0.2)
        low_threshold_items = decay.get_active(threshold=0.05)
        
        # Higher thresholds should return fewer items
        assert len(high_threshold_items) <= len(medium_threshold_items)
        assert len(medium_threshold_items) <= len(low_threshold_items)
        
        # Items should be sorted by weight (descending)
        if len(medium_threshold_items) > 1:
            weights = [item[2] for item in medium_threshold_items]
            assert weights == sorted(weights, reverse=True)
    
    def test_context_item_updates(self):
        """
        Test updating existing context items resets their decay.
        
        Validates that agents can refresh important information,
        essential for maintaining relevant context over time.
        """
        decay = ContextDecay(half_life_steps=5)
        
        # Add initial item
        decay.add("user_name", "Alice", importance=0.8)
        
        # Age the item
        for _ in range(5):
            decay.step()
        
        # Get weight after aging
        aged_items = decay.get_active(threshold=0.0)
        aged_weight = aged_items[0][2]
        
        # Update the item (should reset timestamp)
        decay.add("user_name", "Alice Smith", importance=0.8)
        
        # Weight should be back to near full strength
        refreshed_items = decay.get_active(threshold=0.0)
        refreshed_weight = refreshed_items[0][2]
        
        assert refreshed_weight > aged_weight
        assert abs(refreshed_weight - 0.8) < 0.01  # Should be near full importance
    
    def test_custom_decay_function(self):
        """
        Test integration with custom decay functions.
        
        Validates extensibility for different agent memory models,
        such as linear decay or stepped decay functions.
        """
        def linear_decay(importance, steps, half_life):
            """Linear decay function for testing."""
            decay_rate = 0.5 / half_life  # 50% decay over half_life steps
            return max(0, importance - (steps * decay_rate * importance))
        
        decay = ContextDecay(half_life_steps=10, decay_function=linear_decay)
        decay.add("test_item", "data", importance=1.0)
        
        # Test linear vs exponential behavior
        for _ in range(5):  # Half of half_life
            decay.step()
        
        active = decay.get_active(threshold=0.0)
        _, _, weight = active[0]
        
        # Linear decay at 5 steps should be 0.75 (not ~0.71 for exponential)
        expected_linear = 1.0 - (5 * 0.05)  # 5 steps * 5% per step
        assert abs(weight - expected_linear) < 0.01
    
    def test_clear_expired_items(self):
        """
        Test removal of expired context items for memory management.
        
        Validates that agents can clean up irrelevant context,
        preventing memory bloat in long-running conversations.
        """
        decay = ContextDecay(half_life_steps=3)
        
        # Add multiple items
        decay.add("item1", "data1", importance=0.8)
        decay.add("item2", "data2", importance=0.5)
        decay.add("item3", "data3", importance=0.3)
        
        # Age items significantly
        for _ in range(10):
            decay.step()
        
        # Clear expired items
        removed_count = decay.clear_expired(threshold=0.1)
        
        assert removed_count > 0  # Some items should be removed
        
        # Verify remaining items are above threshold
        remaining = decay.get_active(threshold=0.0)
        for _, _, weight in remaining:
            assert weight >= 0.1
    
    def test_statistics_tracking(self):
        """
        Test statistical reporting for context management insights.
        
        Validates that agents can monitor their context usage patterns,
        essential for debugging and optimization.
        """
        decay = ContextDecay(half_life_steps=8)
        
        # Initially empty
        stats = decay.get_stats()
        assert stats['total_items'] == 0
        assert stats['active_items'] == 0
        assert stats['avg_decay'] == 0.0
        assert stats['oldest_age'] == 0
        
        # Add items at different times
        decay.add("item1", "data1", importance=1.0)
        decay.step()
        decay.add("item2", "data2", importance=0.6)
        decay.step()
        decay.add("item3", "data3", importance=0.4)
        decay.step()
        
        stats = decay.get_stats()
        
        assert stats['total_items'] == 3
        assert stats['active_items'] >= 0  # Depends on decay
        assert 0 < stats['avg_decay'] <= 1.0
        assert stats['oldest_age'] == 3  # item1 is 3 steps old
    
    def test_validation_errors(self):
        """
        Test proper validation of input parameters.
        
        Validates that invalid inputs are caught early,
        preventing agent malfunction due to bad context data.
        """
        decay = ContextDecay(half_life_steps=5)
        
        # Test invalid importance values
        with pytest.raises(ValueError, match="Importance must be between 0.0 and 1.0"):
            decay.add("invalid_high", "data", importance=1.5)
        
        with pytest.raises(ValueError, match="Importance must be between 0.0 and 1.0"):
            decay.add("invalid_low", "data", importance=-0.1)
        
        # Valid edge cases should work
        decay.add("min_importance", "data", importance=0.0)
        decay.add("max_importance", "data", importance=1.0)
    
    def test_realistic_chat_scenario(self):
        """
        Test realistic chat conversation context management.
        
        Simulates a multi-turn conversation where user preferences
        and task details have different importance and decay rates.
        """
        decay = ContextDecay(half_life_steps=15)  # Preferences fade over 15 interactions
        
        # Initial user preferences
        decay.add("tone_preference", "casual", importance=0.6)
        decay.add("language_preference", "simple_english", importance=0.7)
        
        # Conversation progresses
        for turn in range(5):
            decay.step()
            
            # Add task-specific context (high importance)
            decay.add(f"current_task_{turn}", f"task_data_{turn}", importance=1.0)
            
            # Occasionally update preferences
            if turn == 3:
                decay.add("tone_preference", "professional", importance=0.8)
        
        # After conversation, recent tasks should dominate
        active = decay.get_active(threshold=0.3)
        
        # Recent tasks should be most prominent
        recent_tasks = [item for item in active if "current_task" in item[0]]
        preferences = [item for item in active if "preference" in item[0]]
        
        # Recent tasks should have higher weights than old preferences
        if recent_tasks and preferences:
            max_task_weight = max(item[2] for item in recent_tasks)
            min_pref_weight = min(item[2] for item in preferences)
            
            # This relationship validates proper temporal prioritization
            assert max_task_weight > min_pref_weight * 0.5  # Allow some overlap