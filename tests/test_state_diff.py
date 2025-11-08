"""
Comprehensive tests for argentum.state_diff module.

These tests cover real-world scenarios developers encounter when debugging
agent behavior, ensuring the StateDiff class provides actionable insights
for complex agent state tracking.
"""

import pytest
from argentum.state_diff import StateDiff


class TestStateDiff:
    """Test StateDiff functionality across various agent debugging scenarios."""
    
    def test_simple_value_changes(self):
        """
        Test basic value changes like counters and flags.
        
        Scenario: Agent updates simple state variables during execution.
        This is common when tracking tool usage counts, confidence scores,
        or boolean flags that indicate agent mode changes.
        """
        diff = StateDiff()
        
        diff.snapshot("start", {"counter": 0, "active": True, "mode": "idle"})
        diff.snapshot("updated", {"counter": 5, "active": False, "mode": "processing"})
        
        changes = diff.get_changes("start", "updated")
        
        assert changes == {
            "counter": {"from": 0, "to": 5},
            "active": {"from": True, "to": False},
            "mode": {"from": "idle", "to": "processing"}
        }
    
    def test_added_and_removed_keys(self):
        """
        Test detection of added and removed state keys.
        
        Scenario: Agent acquires new capabilities or loses temporary state.
        For example, an agent might gain access to new tools or lose
        session-specific data after completing a task.
        """
        diff = StateDiff()
        
        diff.snapshot("initial", {"core_data": "preserved", "temp_session": "abc123"})
        diff.snapshot("evolved", {"core_data": "preserved", "new_capability": "advanced_search"})
        
        changes = diff.get_changes("initial", "evolved")
        
        assert changes == {
            "temp_session": {"removed": "abc123"},
            "new_capability": {"added": "advanced_search"}
        }
    
    def test_nested_dict_changes(self):
        """
        Test deep nested structure modifications.
        
        Scenario: Agent memory has hierarchical structure with metadata.
        This tests the flattening behavior for complex agent states where
        memory, context, and configuration are deeply nested.
        """
        diff = StateDiff()
        
        initial_state = {
            "agent": {
                "memory": {
                    "facts": ["fact1"],
                    "metadata": {"confidence": 0.8, "source": "search"}
                },
                "config": {"max_depth": 3}
            }
        }
        
        updated_state = {
            "agent": {
                "memory": {
                    "facts": ["fact1", "fact2"],
                    "metadata": {"confidence": 0.9, "source": "analysis", "verified": True}
                },
                "config": {"max_depth": 5, "use_cache": True}
            }
        }
        
        diff.snapshot("before", initial_state)
        diff.snapshot("after", updated_state)
        
        changes = diff.get_changes("before", "after")
        
        expected = {
            "agent.memory.facts": {"added": ["fact2"]},
            "agent.memory.metadata.confidence": {"from": 0.8, "to": 0.9},
            "agent.memory.metadata.source": {"from": "search", "to": "analysis"},
            "agent.memory.metadata.verified": {"added": True},
            "agent.config.max_depth": {"from": 3, "to": 5},
            "agent.config.use_cache": {"added": True}
        }
        
        assert changes == expected
    
    def test_list_operations(self):
        """
        Test list addition and removal tracking.
        
        Scenario: Agent maintains lists of goals, completed tasks, or facts.
        Understanding what gets added or removed from these lists is crucial
        for debugging agent decision-making and task completion.
        """
        diff = StateDiff()
        
        diff.snapshot("start", {
            "goals": ["research_topic", "write_summary"],
            "completed_tasks": ["initialize"],
            "facts": ["sky_blue", "grass_green"]
        })
        
        diff.snapshot("progress", {
            "goals": ["write_summary", "review_draft"],  # research_topic removed, review_draft added
            "completed_tasks": ["initialize", "research_topic"],  # research_topic completed
            "facts": ["sky_blue", "grass_green", "sun_yellow"]  # sun_yellow learned
        })
        
        changes = diff.get_changes("start", "progress")
        
        expected = {
            "goals": {"removed": ["research_topic"], "added": ["review_draft"]},
            "completed_tasks": {"added": ["research_topic"]},
            "facts": {"added": ["sun_yellow"]}
        }
        
        assert changes == expected
    
    def test_complex_agent_state_evolution(self):
        """
        Test realistic multi-step agent state changes.
        
        Scenario: Complete agent execution from initialization through
        multiple reasoning and action steps. This represents a real debugging
        session where developers need to understand agent behavior evolution.
        """
        diff = StateDiff()
        
        # Agent starts with basic initialization
        diff.snapshot("initialization", {
            "memory": {"facts": [], "confidence_scores": {}},
            "goals": ["understand_user_request", "gather_information", "provide_response"],
            "tools": {"search_calls": 0, "analysis_calls": 0},
            "context": {"user_query": "What causes rain?", "session_id": "sess_123"},
            "state": {"current_phase": "understanding", "confidence": 0.0}
        })
        
        # After understanding user request
        diff.snapshot("request_understood", {
            "memory": {"facts": [], "confidence_scores": {}},
            "goals": ["gather_information", "provide_response"],  # understanding completed
            "tools": {"search_calls": 0, "analysis_calls": 1},  # used analysis to understand
            "context": {
                "user_query": "What causes rain?", 
                "session_id": "sess_123",
                "parsed_intent": "scientific_explanation",
                "domain": "meteorology"
            },
            "state": {"current_phase": "information_gathering", "confidence": 0.3}
        })
        
        # After gathering information
        diff.snapshot("information_gathered", {
            "memory": {
                "facts": [
                    "Water evaporates from oceans",
                    "Water vapor condenses in clouds", 
                    "Condensed water falls as precipitation"
                ],
                "confidence_scores": {"evaporation": 0.9, "condensation": 0.8, "precipitation": 0.9}
            },
            "goals": ["provide_response"],  # information gathering completed
            "tools": {"search_calls": 3, "analysis_calls": 2},
            "context": {
                "user_query": "What causes rain?",
                "session_id": "sess_123", 
                "parsed_intent": "scientific_explanation",
                "domain": "meteorology",
                "sources": ["scientific_journal", "weather_service"]
            },
            "state": {"current_phase": "synthesis", "confidence": 0.8}
        })
        
        # Test step-by-step evolution
        changes_1 = diff.get_changes("initialization", "request_understood")
        changes_2 = diff.get_changes("request_understood", "information_gathered")
        
        # Verify first transition: understanding request
        assert "goals" in changes_1
        assert changes_1["goals"]["removed"] == ["understand_user_request"]
        assert changes_1["tools.analysis_calls"] == {"from": 0, "to": 1}
        assert changes_1["context.parsed_intent"] == {"added": "scientific_explanation"}
        assert changes_1["state.current_phase"] == {"from": "understanding", "to": "information_gathering"}
        
        # Verify second transition: gathering information
        assert changes_2["memory.facts"]["added"] == [
            "Water evaporates from oceans",
            "Water vapor condenses in clouds", 
            "Condensed water falls as precipitation"
        ]
        assert changes_2["tools.search_calls"] == {"from": 0, "to": 3}
        assert changes_2["state.confidence"] == {"from": 0.3, "to": 0.8}
    
    def test_sequence_changes(self):
        """
        Test chronological change tracking across multiple snapshots.
        
        Scenario: Developer needs to see the complete evolution timeline
        to understand where agent behavior diverged from expected path.
        """
        diff = StateDiff()
        
        diff.snapshot("step1", {"value": 1, "status": "init"})
        diff.snapshot("step2", {"value": 2, "status": "processing"}) 
        diff.snapshot("step3", {"value": 2, "status": "complete", "result": "success"})
        
        sequence = diff.get_sequence_changes()
        
        assert len(sequence) == 2
        
        # First transition
        assert sequence[0]["from"] == "step1"
        assert sequence[0]["to"] == "step2"
        assert sequence[0]["changes"] == {
            "value": {"from": 1, "to": 2},
            "status": {"from": "init", "to": "processing"}
        }
        
        # Second transition  
        assert sequence[1]["from"] == "step2"
        assert sequence[1]["to"] == "step3"
        assert sequence[1]["changes"] == {
            "status": {"from": "processing", "to": "complete"},
            "result": {"added": "success"}
        }
    
    def test_edge_cases(self):
        """
        Test edge cases: None values, empty states, identical states.
        
        Scenario: Robust handling of edge cases that occur in real agent
        debugging scenarios, such as uninitialized values or empty states.
        """
        diff = StateDiff()
        
        # Test None values
        diff.snapshot("with_none", {"data": None, "count": 0})
        diff.snapshot("none_to_value", {"data": "actual_data", "count": 0})
        
        changes = diff.get_changes("with_none", "none_to_value")
        assert changes == {"data": {"from": None, "to": "actual_data"}}
        
        # Test empty states
        diff.snapshot("empty", {})
        diff.snapshot("populated", {"new_key": "new_value"})
        
        changes = diff.get_changes("empty", "populated")
        assert changes == {"new_key": {"added": "new_value"}}
        
        # Test identical states (no changes)
        diff.snapshot("identical1", {"same": "data"})
        diff.snapshot("identical2", {"same": "data"})
        
        changes = diff.get_changes("identical1", "identical2")
        assert changes == {}
    
    def test_clear_functionality(self):
        """
        Test clearing all snapshots and sequence data.
        
        Scenario: Developer wants to start fresh tracking for a new agent
        session or reset during debugging.
        """
        diff = StateDiff()
        
        diff.snapshot("test1", {"data": 1})
        diff.snapshot("test2", {"data": 2})
        
        assert len(diff._snapshots) == 2
        assert len(diff._sequence) == 2
        
        diff.clear()
        
        assert len(diff._snapshots) == 0
        assert len(diff._sequence) == 0
    
    def test_error_handling(self):
        """
        Test proper error handling for invalid operations.
        
        Scenario: Developer attempts to compare non-existent snapshots,
        which should provide clear error messages for debugging.
        """
        diff = StateDiff()
        
        diff.snapshot("exists", {"data": "value"})
        
        # Test non-existent from_label
        with pytest.raises(KeyError, match="Snapshot 'missing' not found"):
            diff.get_changes("missing", "exists")
        
        # Test non-existent to_label  
        with pytest.raises(KeyError, match="Snapshot 'missing' not found"):
            diff.get_changes("exists", "missing")
    
    def test_performance_monitoring_use_case(self):
        """
        Test performance monitoring scenario with timing and resource tracking.
        
        Scenario: Developer tracks agent performance metrics to identify
        bottlenecks and optimize agent behavior for production deployment.
        """
        diff = StateDiff()
        
        diff.snapshot("start_task", {
            "performance": {
                "memory_usage_mb": 45.2,
                "response_time_ms": 0,
                "api_calls": {"total": 0, "search": 0, "llm": 0}
            },
            "task_state": "initialized"
        })
        
        diff.snapshot("after_search", {
            "performance": {
                "memory_usage_mb": 67.8,
                "response_time_ms": 1250,
                "api_calls": {"total": 3, "search": 3, "llm": 0}
            },
            "task_state": "data_gathered"
        })
        
        diff.snapshot("task_complete", {
            "performance": {
                "memory_usage_mb": 52.1,
                "response_time_ms": 2100,
                "api_calls": {"total": 5, "search": 3, "llm": 2}
            },
            "task_state": "completed"
        })
        
        # Analyze performance changes during search phase
        search_changes = diff.get_changes("start_task", "after_search")
        
        assert search_changes["performance.memory_usage_mb"]["from"] == 45.2
        assert search_changes["performance.memory_usage_mb"]["to"] == 67.8
        assert search_changes["performance.api_calls.search"]["from"] == 0
        assert search_changes["performance.api_calls.search"]["to"] == 3
        
        # Analyze complete sequence for performance optimization
        sequence = diff.get_sequence_changes()
        
        # Should show memory cleanup after processing
        completion_changes = sequence[1]["changes"]
        assert completion_changes["performance.memory_usage_mb"]["from"] == 67.8
        assert completion_changes["performance.memory_usage_mb"]["to"] == 52.1