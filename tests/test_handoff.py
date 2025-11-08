"""
Comprehensive tests for argentum.handoff module.

These tests cover real-world multi-agent scenarios ensuring the HandoffProtocol
provides reliable context transfer and prevents information loss between agents.
"""

import json
import pytest
from datetime import datetime
from argentum.handoff import Handoff, HandoffProtocol


class TestHandoff:
    """Test Handoff dataclass functionality."""
    
    def test_handoff_creation_with_defaults(self):
        """
        Test basic handoff creation with automatic field population.
        
        Scenario: Agent creates minimal handoff and system fills in
        required fields like timestamp and handoff_id automatically.
        """
        handoff = Handoff(
            from_agent="researcher",
            to_agent="writer",
            context_summary="Research completed on quantum computing",
            artifacts=["research/quantum_papers.json"],
            confidence=0.85
        )
        
        assert handoff.from_agent == "researcher"
        assert handoff.to_agent == "writer"
        assert handoff.context_summary == "Research completed on quantum computing"
        assert handoff.artifacts == ["research/quantum_papers.json"]
        assert handoff.confidence == 0.85
        assert handoff.timestamp is not None
        assert handoff.handoff_id is not None
        assert handoff.metadata == {}
        assert handoff.suggested_next_action is None
    
    def test_handoff_creation_with_all_fields(self):
        """
        Test handoff creation with all fields specified.
        
        Scenario: Agent provides complete handoff information including
        metadata for framework-specific data and suggested next action.
        """
        handoff = Handoff(
            from_agent="data_analyzer",
            to_agent="report_generator",
            context_summary="Analyzed customer feedback, found 3 key themes",
            artifacts=["analysis/themes.csv", "analysis/sentiment_scores.json"],
            confidence=0.92,
            suggested_next_action="generate_executive_summary",
            metadata={"analysis_method": "nlp", "sample_size": 1500},
            timestamp="2024-01-15T10:30:00",
            handoff_id="custom-handoff-123"
        )
        
        assert handoff.suggested_next_action == "generate_executive_summary"
        assert handoff.metadata["analysis_method"] == "nlp"
        assert handoff.timestamp == "2024-01-15T10:30:00"
        assert handoff.handoff_id == "custom-handoff-123"
    
    def test_confidence_validation(self):
        """
        Test confidence score validation enforces 0-1 bounds.
        
        Scenario: Prevent invalid confidence values that would break
        downstream decision-making logic in multi-agent systems.
        """
        # Test valid confidence values
        for valid_conf in [0.0, 0.5, 1.0]:
            handoff = Handoff(
                from_agent="test", to_agent="test", 
                context_summary="test", artifacts=[], 
                confidence=valid_conf
            )
            assert handoff.confidence == valid_conf
        
        # Test invalid confidence values
        for invalid_conf in [-0.1, 1.1, 2.0]:
            with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
                Handoff(
                    from_agent="test", to_agent="test",
                    context_summary="test", artifacts=[],
                    confidence=invalid_conf
                )


class TestHandoffProtocol:
    """Test HandoffProtocol functionality for agent integration."""
    
    def test_create_handoff(self):
        """
        Test handoff creation through protocol interface.
        
        Scenario: Agent uses protocol to create handoff with validation
        and proper defaults for integration consistency.
        """
        protocol = HandoffProtocol()
        
        handoff = protocol.create_handoff(
            from_agent="requirement_analyzer",
            to_agent="system_architect", 
            context_summary="Analyzed user requirements, identified 5 core features",
            artifacts=["requirements/user_stories.md", "requirements/acceptance_criteria.json"],
            suggested_next_action="design_system_architecture",
            confidence=0.88,
            metadata={"complexity": "medium", "estimated_hours": 40}
        )
        
        assert handoff.from_agent == "requirement_analyzer"
        assert handoff.to_agent == "system_architect"
        assert handoff.confidence == 0.88
        assert handoff.metadata["complexity"] == "medium"
        assert handoff.suggested_next_action == "design_system_architecture"
    
    def test_json_serialization_round_trip(self):
        """
        Test complete serialization/deserialization cycle.
        
        Scenario: REST API integration where handoffs are serialized
        for HTTP transfer and deserialized on receiving end.
        """
        protocol = HandoffProtocol()
        
        original = protocol.create_handoff(
            from_agent="code_generator",
            to_agent="code_tester",
            context_summary="Generated authentication module with JWT support",
            artifacts=["src/auth/jwt_handler.py", "src/auth/user_model.py"],
            suggested_next_action="write_unit_tests", 
            confidence=0.79,
            metadata={"framework": "fastapi", "test_coverage_target": 0.9}
        )
        
        # Serialize to JSON
        json_str = protocol.to_json(original)
        
        # Verify JSON structure
        json_data = json.loads(json_str)
        assert json_data["from_agent"] == "code_generator"
        assert json_data["to_agent"] == "code_tester"
        assert json_data["confidence"] == 0.79
        
        # Deserialize back to object
        restored = protocol.from_json(json_str)
        
        # Verify complete round-trip
        assert restored.from_agent == original.from_agent
        assert restored.to_agent == original.to_agent
        assert restored.context_summary == original.context_summary
        assert restored.artifacts == original.artifacts
        assert restored.confidence == original.confidence
        assert restored.suggested_next_action == original.suggested_next_action
        assert restored.metadata == original.metadata
        assert restored.timestamp == original.timestamp
        assert restored.handoff_id == original.handoff_id
    
    def test_handoff_validation(self):
        """
        Test validation logic for handoff completeness.
        
        Scenario: Prevent malformed handoffs that would cause failures
        in downstream agent processing or integration systems.
        """
        protocol = HandoffProtocol()
        
        # Valid handoff should pass
        valid_handoff = protocol.create_handoff(
            "agent_a", "agent_b", "Work completed", ["artifact.txt"]
        )
        assert protocol.validate_handoff(valid_handoff) is True
        
        # Test various invalid scenarios
        invalid_cases = [
            # Empty from_agent
            Handoff("", "agent_b", "summary", [], 0.8),
            # Empty to_agent  
            Handoff("agent_a", "", "summary", [], 0.8),
            # Empty context_summary
            Handoff("agent_a", "agent_b", "", [], 0.8),
        ]
        
        for invalid_handoff in invalid_cases:
            with pytest.raises(ValueError):
                protocol.validate_handoff(invalid_handoff)
        
        # Test invalid artifacts type
        invalid_artifacts_handoff = Handoff(
            "agent_a", "agent_b", "summary", "not_a_list", 0.8
        )
        with pytest.raises(ValueError, match="artifacts must be a list"):
            protocol.validate_handoff(invalid_artifacts_handoff)
    
    def test_receipt_generation(self):
        """
        Test acknowledgment receipt creation for handoff tracking.
        
        Scenario: Message queue integration where receiving agent
        sends acknowledgment receipt back to sender for monitoring.
        """
        protocol = HandoffProtocol()
        
        handoff = protocol.create_handoff(
            from_agent="task_planner",
            to_agent="task_executor", 
            context_summary="Created deployment plan for microservices",
            artifacts=["deployment/k8s-manifests.yaml", "deployment/helm-chart.yaml"],
            confidence=0.95
        )
        
        receipt = protocol.generate_receipt(handoff, "received_and_processing")
        
        assert receipt["handoff_id"] == handoff.handoff_id
        assert receipt["from_agent"] == "task_planner"
        assert receipt["to_agent"] == "task_executor" 
        assert receipt["status"] == "received_and_processing"
        assert "received_at" in receipt
        assert receipt["original_timestamp"] == handoff.timestamp
        
        # Verify timestamp format
        datetime.fromisoformat(receipt["received_at"])  # Should not raise
    
    def test_realistic_research_pipeline(self):
        """
        Test complete research pipeline handoff scenario.
        
        Scenario: Multi-stage research workflow where each agent hands off
        to the next with accumulated context and artifacts.
        """
        protocol = HandoffProtocol()
        
        # Stage 1: Researcher → Fact Checker
        research_handoff = protocol.create_handoff(
            from_agent="primary_researcher",
            to_agent="fact_checker",
            context_summary="Researched renewable energy trends. Found 15 sources, 8 high-quality papers.",
            artifacts=[
                "research/renewable_energy_papers.json",
                "research/industry_reports.pdf", 
                "research/expert_interviews.md"
            ],
            suggested_next_action="verify_statistics_and_claims",
            confidence=0.87,
            metadata={
                "research_method": "systematic_review",
                "search_databases": ["IEEE", "ScienceDirect", "Google Scholar"],
                "date_range": "2020-2024"
            }
        )
        
        # Stage 2: Fact Checker → Writer  
        fact_check_handoff = protocol.create_handoff(
            from_agent="fact_checker",
            to_agent="technical_writer",
            context_summary="Verified 12/15 sources. Flagged 3 statistics for update. All major claims validated.",
            artifacts=[
                "research/renewable_energy_papers.json",
                "fact_check/verified_sources.json",
                "fact_check/flagged_items.md",
                "fact_check/validation_report.pdf"
            ],
            suggested_next_action="draft_technical_article",
            confidence=0.91,
            metadata={
                "verification_method": "cross_reference",
                "sources_verified": 12,
                "sources_flagged": 3,
                "confidence_boost": 0.04
            }
        )
        
        # Verify handoff chain integrity
        assert research_handoff.to_agent == fact_check_handoff.from_agent
        assert "research/renewable_energy_papers.json" in research_handoff.artifacts
        assert "research/renewable_energy_papers.json" in fact_check_handoff.artifacts
        assert fact_check_handoff.confidence > research_handoff.confidence
    
    def test_code_generation_pipeline(self):
        """
        Test software development pipeline with handoffs.
        
        Scenario: Code generation workflow where artifacts and context
        accumulate through architect → coder → tester stages.
        """
        protocol = HandoffProtocol()
        
        # Architect → Coder
        arch_handoff = protocol.create_handoff(
            from_agent="system_architect", 
            to_agent="senior_developer",
            context_summary="Designed microservice architecture for user management system",
            artifacts=[
                "architecture/service_diagram.mmd",
                "architecture/api_specs.yaml", 
                "architecture/database_schema.sql"
            ],
            suggested_next_action="implement_user_service",
            confidence=0.93,
            metadata={
                "architecture_pattern": "hexagonal",
                "estimated_complexity": "medium",
                "target_framework": "spring_boot"
            }
        )
        
        # Coder → Tester
        code_handoff = protocol.create_handoff(
            from_agent="senior_developer",
            to_agent="qa_engineer", 
            context_summary="Implemented user service with JWT auth. 85% code coverage achieved.",
            artifacts=[
                "src/user-service/UserController.java",
                "src/user-service/UserService.java",
                "src/user-service/JwtTokenProvider.java",
                "tests/user-service/UserServiceTest.java"
            ],
            suggested_next_action="run_integration_tests",
            confidence=0.82,
            metadata={
                "implementation_time_hours": 16,
                "code_coverage": 0.85,
                "known_issues": ["rate_limiting_not_implemented"]
            }
        )
        
        # Verify artifacts flow through pipeline
        assert arch_handoff.metadata["target_framework"] == "spring_boot"
        assert code_handoff.metadata["code_coverage"] == 0.85
        assert "src/user-service/UserController.java" in code_handoff.artifacts
    
    def test_edge_cases_and_error_handling(self):
        """
        Test edge cases and error conditions.
        
        Scenario: Robust handling of malformed data and edge cases
        that occur in production multi-agent systems.
        """
        protocol = HandoffProtocol()
        
        # Test empty artifacts list (valid)
        handoff = protocol.create_handoff(
            "agent_a", "agent_b", "No artifacts produced", []
        )
        assert handoff.artifacts == []
        
        # Test zero confidence (valid but unusual)
        handoff = protocol.create_handoff(
            "agent_a", "agent_b", "Very uncertain results", [], confidence=0.0
        )
        assert handoff.confidence == 0.0
        
        # Test malformed JSON deserialization
        with pytest.raises(json.JSONDecodeError):
            protocol.from_json("invalid json {")
        
        # Test missing required fields in JSON
        incomplete_json = json.dumps({"from_agent": "test"})
        with pytest.raises(TypeError):  # Missing required fields
            protocol.from_json(incomplete_json)