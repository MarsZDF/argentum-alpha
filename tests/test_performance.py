"""
Performance tests and benchmarks for argentum modules.

These tests ensure the modules perform well under realistic workloads
and help identify performance regressions during development.
"""

import pytest
import time
import random
import string
from argentum import StateDiff, ContextDecay, Handoff, HandoffProtocol

# Only run performance tests if benchmark plugin is available
pytest_benchmark = pytest.importorskip("pytest_benchmark")


class TestStateDiffPerformance:
    """Performance tests for StateDiff module."""
    
    def generate_state(self, size="small"):
        """Generate test states of different sizes."""
        if size == "small":
            return {
                "memory": ["fact_" + str(i) for i in range(10)],
                "goals": ["goal_" + str(i) for i in range(5)],
                "confidence": random.random(),
                "tools_used": {"search": random.randint(0, 10), "analyze": random.randint(0, 5)}
            }
        elif size == "medium":
            return {
                "memory": {
                    "facts": ["fact_" + str(i) for i in range(100)],
                    "metadata": {f"key_{i}": f"value_{i}" for i in range(50)},
                    "confidence_scores": {f"topic_{i}": random.random() for i in range(30)}
                },
                "goals": ["goal_" + str(i) for i in range(20)],
                "context": {f"context_{i}": f"data_{i}" for i in range(100)},
                "reasoning_state": {
                    "current_strategy": "comprehensive_analysis",
                    "depth": 3,
                    "confidence": random.random()
                }
            }
        else:  # large
            return {
                "memory": {
                    "facts": ["fact_" + ''.join(random.choices(string.ascii_lowercase, k=20)) for i in range(1000)],
                    "sources": [f"source_{i}.pdf" for i in range(500)],
                    "metadata": {f"meta_key_{i}": f"meta_value_{i}_{''.join(random.choices(string.ascii_lowercase, k=50))}" for i in range(200)},
                    "confidence_scores": {f"topic_{i}": random.random() for i in range(300)}
                },
                "goals": [f"goal_{i}_{''.join(random.choices(string.ascii_lowercase, k=30))}" for i in range(100)],
                "context": {f"context_{i}": ''.join(random.choices(string.ascii_lowercase, k=100)) for i in range(500)},
                "tools_used": {f"tool_{i}": random.randint(0, 100) for i in range(50)},
                "reasoning_history": [{"step": i, "thought": ''.join(random.choices(string.ascii_lowercase, k=200))} for i in range(200)]
            }
    
    def test_snapshot_performance_small(self, benchmark):
        """Benchmark snapshot creation with small states."""
        diff = StateDiff()
        state = self.generate_state("small")
        
        result = benchmark(diff.snapshot, "test", state)
        assert result is None  # snapshot returns None
    
    def test_snapshot_performance_medium(self, benchmark):
        """Benchmark snapshot creation with medium states."""
        diff = StateDiff()
        state = self.generate_state("medium")
        
        result = benchmark(diff.snapshot, "test", state)
        assert result is None
    
    def test_snapshot_performance_large(self, benchmark):
        """Benchmark snapshot creation with large states."""
        diff = StateDiff()
        state = self.generate_state("large")
        
        result = benchmark(diff.snapshot, "test", state)
        assert result is None
    
    def test_diff_computation_performance(self, benchmark):
        """Benchmark diff computation between complex states."""
        diff = StateDiff()
        
        state1 = self.generate_state("medium")
        state2 = self.generate_state("medium")
        state2["memory"]["facts"].append("new_fact")
        state2["goals"].pop()
        state2["context"]["new_key"] = "new_value"
        
        diff.snapshot("before", state1)
        diff.snapshot("after", state2)
        
        result = benchmark(diff.get_changes, "before", "after")
        assert isinstance(result, dict)
        assert len(result) > 0
    
    def test_sequence_changes_performance(self, benchmark):
        """Benchmark sequence change computation with multiple snapshots."""
        diff = StateDiff()
        
        # Create a sequence of 10 states with gradual changes
        base_state = self.generate_state("medium")
        
        for i in range(10):
            state = base_state.copy()
            state["memory"]["facts"].append(f"fact_step_{i}")
            state["goals"] = state["goals"][:-1] if state["goals"] else []
            state["step"] = i
            diff.snapshot(f"step_{i}", state)
        
        result = benchmark(diff.get_sequence_changes)
        assert isinstance(result, list)
        assert len(result) == 9  # 10 snapshots = 9 transitions
    
    def test_memory_usage_snapshots(self):
        """Test memory usage with many snapshots (not timed)."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        diff = StateDiff()
        
        # Create many snapshots
        for i in range(1000):
            state = self.generate_state("small")
            state["iteration"] = i
            diff.snapshot(f"snapshot_{i}", state)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        memory_increase_mb = memory_increase / (1024 * 1024)
        
        # Memory increase should be reasonable (less than 100MB for 1000 small snapshots)
        assert memory_increase_mb < 100, f"Memory usage too high: {memory_increase_mb:.1f}MB"
        
        print(f"Memory increase for 1000 snapshots: {memory_increase_mb:.1f}MB")


class TestContextDecayPerformance:
    """Performance tests for ContextDecay module."""
    
    def test_add_performance(self, benchmark):
        """Benchmark adding context items."""
        decay = ContextDecay(half_life_steps=10)
        
        def add_item():
            key = ''.join(random.choices(string.ascii_lowercase, k=10))
            value = ''.join(random.choices(string.ascii_lowercase, k=50))
            decay.add(key, value, importance=random.random())
        
        result = benchmark(add_item)
        assert result is None
    
    def test_step_performance(self, benchmark):
        """Benchmark time advancement with many items."""
        decay = ContextDecay(half_life_steps=10)
        
        # Add many items
        for i in range(1000):
            decay.add(f"key_{i}", f"value_{i}", importance=random.random())
        
        result = benchmark(decay.step)
        assert result is None
    
    def test_get_active_performance(self, benchmark):
        """Benchmark retrieving active items."""
        decay = ContextDecay(half_life_steps=10)
        
        # Add items with varying ages
        for i in range(500):
            decay.add(f"key_{i}", f"value_{i}", importance=random.random())
            if i % 10 == 0:
                decay.step()
        
        result = benchmark(decay.get_active, 0.3)
        assert isinstance(result, list)
    
    def test_clear_expired_performance(self, benchmark):
        """Benchmark clearing expired items."""
        decay = ContextDecay(half_life_steps=5)
        
        # Add many items and age them
        for i in range(1000):
            decay.add(f"key_{i}", f"value_{i}", importance=random.uniform(0.1, 1.0))
        
        # Age items significantly
        for _ in range(20):
            decay.step()
        
        result = benchmark(decay.clear_expired, 0.1)
        assert isinstance(result, int)
        assert result >= 0
    
    def test_large_context_decay_simulation(self):
        """Simulate realistic long-running agent with context decay."""
        decay = ContextDecay(half_life_steps=50)
        
        start_time = time.time()
        
        # Simulate 1000 conversation turns
        for turn in range(1000):
            # Add various types of context
            if turn % 5 == 0:  # User preference
                decay.add("user_preference", f"pref_{turn}", importance=0.7)
            
            if turn % 3 == 0:  # Current task
                decay.add("current_task", f"task_{turn}", importance=1.0)
            
            if turn % 2 == 0:  # Facts learned
                decay.add(f"fact_{turn}", f"learned_fact_{turn}", importance=random.uniform(0.4, 0.9))
            
            # Regular context items
            decay.add(f"context_{turn}", f"context_data_{turn}", importance=random.uniform(0.2, 0.8))
            
            # Advance time
            decay.step()
            
            # Periodic cleanup
            if turn % 100 == 99:
                decay.clear_expired(threshold=0.1)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        stats = decay.get_stats()
        active_items = decay.get_active(threshold=0.2)
        
        print(f"1000-turn simulation completed in {elapsed:.2f}s")
        print(f"Final stats: {stats}")
        print(f"Active items: {len(active_items)}")
        
        # Should complete in reasonable time
        assert elapsed < 10.0, f"Simulation took too long: {elapsed:.2f}s"


class TestHandoffPerformance:
    """Performance tests for Handoff module."""
    
    def test_handoff_creation_performance(self, benchmark):
        """Benchmark handoff creation."""
        def create_handoff():
            return Handoff(
                from_agent="test_agent_" + ''.join(random.choices(string.ascii_lowercase, k=10)),
                to_agent="target_agent_" + ''.join(random.choices(string.ascii_lowercase, k=10)),
                context_summary="Summary: " + ''.join(random.choices(string.ascii_lowercase, k=100)),
                artifacts=[f"artifact_{i}.txt" for i in range(10)],
                confidence=random.random(),
                metadata={f"key_{i}": f"value_{i}" for i in range(20)}
            )
        
        result = benchmark(create_handoff)
        assert isinstance(result, Handoff)
    
    def test_json_serialization_performance(self, benchmark):
        """Benchmark JSON serialization of handoffs."""
        protocol = HandoffProtocol()
        
        # Create a complex handoff
        handoff = Handoff(
            from_agent="complex_agent",
            to_agent="target_agent",
            context_summary="Complex handoff with lots of data: " + ''.join(random.choices(string.ascii_lowercase, k=1000)),
            artifacts=[f"large_artifact_{i}.json" for i in range(100)],
            confidence=0.85,
            metadata={
                "large_data": {f"key_{i}": ''.join(random.choices(string.ascii_lowercase, k=100)) for i in range(100)},
                "metrics": {f"metric_{i}": random.random() for i in range(50)},
                "config": {"setting_" + str(i): random.choice([True, False, "auto"]) for i in range(30)}
            }
        )
        
        result = benchmark(protocol.to_json, handoff)
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_json_deserialization_performance(self, benchmark):
        """Benchmark JSON deserialization of handoffs."""
        protocol = HandoffProtocol()
        
        # Create and serialize a handoff
        handoff = Handoff(
            from_agent="test_agent",
            to_agent="target_agent", 
            context_summary="Test handoff " + ''.join(random.choices(string.ascii_lowercase, k=500)),
            artifacts=[f"artifact_{i}.txt" for i in range(50)],
            confidence=0.75,
            metadata={f"key_{i}": f"value_{i}_{''.join(random.choices(string.ascii_lowercase, k=50))}" for i in range(50)}
        )
        
        json_data = protocol.to_json(handoff)
        
        result = benchmark(protocol.from_json, json_data)
        assert isinstance(result, Handoff)
        assert result.from_agent == handoff.from_agent
    
    def test_handoff_validation_performance(self, benchmark):
        """Benchmark handoff validation."""
        protocol = HandoffProtocol()
        
        handoff = Handoff(
            from_agent="validation_agent",
            to_agent="target_agent",
            context_summary="Validation test",
            artifacts=["test.txt"],
            confidence=0.8
        )
        
        result = benchmark(protocol.validate_handoff, handoff)
        assert result is True
    
    def test_high_volume_handoff_processing(self):
        """Test processing many handoffs quickly."""
        protocol = HandoffProtocol()
        
        start_time = time.time()
        handoffs = []
        
        # Create 10,000 handoffs
        for i in range(10000):
            handoff = protocol.create_handoff(
                from_agent=f"agent_{i % 100}",
                to_agent=f"target_{(i + 1) % 100}",
                context_summary=f"Handoff {i} summary",
                artifacts=[f"file_{i}.txt"],
                confidence=random.random()
            )
            handoffs.append(handoff)
        
        # Serialize all handoffs
        serialized = []
        for handoff in handoffs:
            json_data = protocol.to_json(handoff)
            serialized.append(json_data)
        
        # Deserialize all handoffs
        deserialized = []
        for json_data in serialized:
            handoff = protocol.from_json(json_data)
            deserialized.append(handoff)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        print(f"Processed 10,000 handoffs in {elapsed:.2f}s")
        print(f"Rate: {10000/elapsed:.0f} handoffs/second")
        
        # Should process at least 1000 handoffs per second
        assert 10000/elapsed > 1000, f"Processing rate too slow: {10000/elapsed:.0f}/sec"
        
        # Verify integrity
        assert len(deserialized) == 10000
        assert deserialized[0].from_agent == handoffs[0].from_agent


try:
    from argentum.plan_lint import PlanLinter
    PLAN_LINT_AVAILABLE = True
except ImportError:
    PLAN_LINT_AVAILABLE = False


@pytest.mark.skipif(not PLAN_LINT_AVAILABLE, reason="PlanLinter requires optional dependencies")
class TestPlanLintPerformance:
    """Performance tests for PlanLinter module."""
    
    def generate_plan(self, steps_count=10):
        """Generate a test plan with specified number of steps."""
        steps = []
        
        for i in range(steps_count):
            step = {
                "id": f"step_{i}",
                "tool": random.choice(["fetch_data", "clean_data", "analyze_trends", "create_visualization"]),
                "parameters": {
                    "param_" + str(j): f"value_{j}" for j in range(random.randint(2, 8))
                }
            }
            
            if i > 0:
                # Add dependencies to some steps
                if random.random() < 0.7:
                    deps = [f"step_{j}" for j in range(max(0, i-2), i) if random.random() < 0.5]
                    if deps:
                        step["depends_on"] = deps[:2]  # Limit dependencies
            
            if random.random() < 0.8:
                step["outputs"] = [f"output_{i}_{j}" for j in range(random.randint(1, 3))]
            
            steps.append(step)
        
        return {"description": f"Generated plan with {steps_count} steps", "steps": steps}
    
    def generate_tool_specs(self, tool_count=10):
        """Generate tool specifications."""
        specs = {}
        
        tool_names = ["fetch_data", "clean_data", "analyze_trends", "create_visualization", 
                      "send_report", "process_data", "validate_results", "format_output",
                      "backup_data", "monitor_performance"]
        
        for i in range(min(tool_count, len(tool_names))):
            tool_name = tool_names[i]
            specs[tool_name] = {
                "parameters": {
                    f"param_{j}": {
                        "type": random.choice(["string", "integer", "boolean", "number"]),
                        "required": random.choice([True, False])
                    } for j in range(random.randint(2, 6))
                }
            }
        
        return specs
    
    def test_small_plan_linting_performance(self, benchmark):
        """Benchmark linting small plans (5 steps)."""
        if not PLAN_LINT_AVAILABLE:
            pytest.skip("PlanLinter not available")
        
        linter = PlanLinter()
        plan = self.generate_plan(5)
        tool_specs = self.generate_tool_specs(5)
        
        result = benchmark(linter.lint, plan, tool_specs)
        assert hasattr(result, 'issues')
    
    def test_medium_plan_linting_performance(self, benchmark):
        """Benchmark linting medium plans (20 steps)."""
        if not PLAN_LINT_AVAILABLE:
            pytest.skip("PlanLinter not available")
        
        linter = PlanLinter()
        plan = self.generate_plan(20)
        tool_specs = self.generate_tool_specs(10)
        
        result = benchmark(linter.lint, plan, tool_specs)
        assert hasattr(result, 'issues')
    
    def test_large_plan_linting_performance(self, benchmark):
        """Benchmark linting large plans (100 steps)."""
        if not PLAN_LINT_AVAILABLE:
            pytest.skip("PlanLinter not available")
        
        linter = PlanLinter()
        plan = self.generate_plan(100)
        tool_specs = self.generate_tool_specs(20)
        
        result = benchmark(linter.lint, plan, tool_specs)
        assert hasattr(result, 'issues')
    
    def test_complex_dependency_analysis_performance(self):
        """Test performance with complex dependency graphs."""
        if not PLAN_LINT_AVAILABLE:
            pytest.skip("PlanLinter not available")
        
        linter = PlanLinter()
        
        # Create a plan with complex dependencies
        steps = []
        for i in range(50):
            step = {
                "id": f"step_{i}",
                "tool": "analyze_trends",
                "parameters": {"data": f"data_{i}"},
                "outputs": [f"output_{i}"]
            }
            
            # Create a complex dependency pattern
            if i > 0:
                deps = []
                # Depend on previous step
                deps.append(f"step_{i-1}")
                # Depend on some earlier steps
                for j in range(max(0, i-5), i-1):
                    if random.random() < 0.3:
                        deps.append(f"step_{j}")
                
                step["depends_on"] = list(set(deps))  # Remove duplicates
            
            steps.append(step)
        
        plan = {"description": "Complex dependency plan", "steps": steps}
        tool_specs = {"analyze_trends": {"parameters": {"data": {"type": "string", "required": True}}}}
        
        start_time = time.time()
        result = linter.lint(plan, tool_specs)
        end_time = time.time()
        
        elapsed = end_time - start_time
        print(f"Complex dependency analysis completed in {elapsed:.3f}s")
        
        # Should complete in reasonable time
        assert elapsed < 5.0, f"Dependency analysis took too long: {elapsed:.3f}s"


class TestMemoryUsage:
    """Test memory usage patterns of all modules."""
    
    def test_state_diff_memory_efficiency(self):
        """Test StateDiff memory usage with large states."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        diff = StateDiff()
        
        # Create a large state
        large_state = {
            "huge_list": [f"item_{i}" for i in range(10000)],
            "huge_dict": {f"key_{i}": f"value_{i}_" + "x" * 100 for i in range(1000)},
            "nested_data": {
                "level1": {
                    "level2": {
                        f"deep_key_{i}": f"deep_value_{i}" for i in range(500)
                    } for _ in range(10)
                }
            }
        }
        
        # Take multiple snapshots
        for i in range(10):
            state_copy = large_state.copy()
            state_copy["iteration"] = i
            state_copy["huge_list"].append(f"new_item_{i}")
            diff.snapshot(f"snapshot_{i}", state_copy)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        memory_increase_mb = memory_increase / (1024 * 1024)
        
        print(f"StateDiff memory increase: {memory_increase_mb:.1f}MB for large states")
        
        # Memory should be reasonable (less than 200MB for this test)
        assert memory_increase_mb < 200, f"StateDiff using too much memory: {memory_increase_mb:.1f}MB"
    
    def test_context_decay_memory_cleanup(self):
        """Test ContextDecay memory cleanup efficiency."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        decay = ContextDecay(half_life_steps=5)
        
        # Add many items
        for i in range(5000):
            large_value = "x" * 1000  # 1KB per item
            decay.add(f"key_{i}", large_value, importance=random.random())
        
        # Age items significantly to trigger decay
        for _ in range(30):
            decay.step()
        
        memory_before_cleanup = process.memory_info().rss
        
        # Clear expired items
        removed = decay.clear_expired(threshold=0.1)
        
        memory_after_cleanup = process.memory_info().rss
        final_memory = memory_after_cleanup
        
        memory_increase = memory_before_cleanup - initial_memory
        memory_freed = memory_before_cleanup - memory_after_cleanup
        total_increase = final_memory - initial_memory
        
        print(f"ContextDecay added {memory_increase / (1024*1024):.1f}MB")
        print(f"Cleanup freed {memory_freed / (1024*1024):.1f}MB")
        print(f"Final increase: {total_increase / (1024*1024):.1f}MB")
        print(f"Items removed: {removed}")
        
        # Should have freed significant memory
        assert memory_freed > memory_increase * 0.5, "Memory cleanup not effective enough"


def test_benchmark_summary(benchmark):
    """Summary test to ensure benchmark plugin works."""
    def simple_operation():
        return sum(range(1000))
    
    result = benchmark(simple_operation)
    assert result == 499500