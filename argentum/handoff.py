"""
Standardized protocol for agent-to-agent handoffs in multi-agent systems.

This module provides a framework-agnostic way to transfer context, artifacts,
and suggested actions between specialized agents, ensuring smooth collaboration
and preventing information loss.

Common Workflows:
    1. Researcher → Writer: Research findings to article draft
    2. Planner → Executor: Task plan to implementation  
    3. Analyzer → Reporter: Data analysis to presentation
    4. Validator → Fixer: Error detection to correction

Example:
    >>> protocol = HandoffProtocol()
    >>> handoff = protocol.create_handoff(
    ...     from_agent="researcher",
    ...     to_agent="writer", 
    ...     context_summary="Found 3 peer-reviewed sources on quantum computing",
    ...     artifacts=["papers/source1.pdf", "papers/source2.pdf"],
    ...     suggested_next_action="synthesize_into_introduction",
    ...     confidence=0.85
    ... )
    >>> json_data = protocol.to_json(handoff)  # For network transfer
    >>> # Send to writer agent...

Integration Patterns:
    - REST API: Serialize to JSON for HTTP transfer
    - Message Queue: Use as message format in RabbitMQ/Kafka
    - Function Calls: Direct handoff in same process
    - File System: Save handoffs for async processing
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid


@dataclass
class Handoff:
    """
    Standardized container for agent-to-agent context transfer.
    
    This dataclass encapsulates all information needed for one agent to hand off
    work to another, ensuring continuity and preventing information loss in
    multi-agent workflows.
    
    Attributes:
        from_agent: Identifier of the sending agent (e.g., "researcher_v2", "planner").
                   Used for tracking handoff chains and debugging agent interactions.
        
        to_agent: Identifier of the receiving agent (e.g., "writer_v1", "executor").
                 Enables routing in multi-agent systems and specialization targeting.
        
        context_summary: Concise summary of work done and current state.
                        Should answer: "What has been accomplished?" and "What's the current situation?"
                        Examples: "Analyzed 50 customer reviews, found 3 key themes",
                                 "Generated code for user auth, needs testing"
        
        artifacts: List of file paths, URLs, or identifiers for work products.
                  Examples: ["data/analysis.csv", "reports/findings.md"],
                           ["https://api.example.com/data/123", "temp/processed_data.json"]
        
        suggested_next_action: Optional hint for the receiving agent's next step.
                             Improves coordination by providing context-specific guidance.
                             Examples: "synthesize_findings", "run_unit_tests", "format_for_presentation"
        
        confidence: Float between 0-1 indicating sender's confidence in the handoff quality.
                   0.9+ = High confidence, work is solid
                   0.7-0.9 = Medium confidence, may need validation  
                   0.7- = Low confidence, significant uncertainty
        
        metadata: Extensible dict for framework-specific data, agent settings, or custom fields.
                 Examples: {"model_version": "gpt-4", "temperature": 0.1},
                          {"deadline": "2024-01-15", "priority": "high"}
        
        timestamp: ISO format timestamp when handoff was created.
                  Used for timeout logic, retry mechanisms, and audit trails.
        
        handoff_id: Unique identifier for tracking this specific handoff.
                   Essential for acknowledgments, error reporting, and debugging.
    
    Examples:
        Research to Writing handoff:
        >>> Handoff(
        ...     from_agent="researcher",
        ...     to_agent="writer", 
        ...     context_summary="Researched quantum computing applications in finance. Found 12 relevant papers.",
        ...     artifacts=["research/quantum_finance_papers.json", "research/key_quotes.md"],
        ...     suggested_next_action="write_introduction_section",
        ...     confidence=0.88
        ... )
        
        Planning to Execution handoff:
        >>> Handoff(
        ...     from_agent="task_planner",
        ...     to_agent="code_executor",
        ...     context_summary="Created implementation plan for user authentication system.",
        ...     artifacts=["plans/auth_architecture.md", "plans/implementation_steps.json"],
        ...     suggested_next_action="implement_user_model",
        ...     confidence=0.92,
        ...     metadata={"estimated_time_hours": 8, "complexity": "medium"}
        ... )
    """
    from_agent: str
    to_agent: str  
    context_summary: str
    artifacts: List[str]
    confidence: float
    suggested_next_action: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    handoff_id: Optional[str] = None
    
    def __post_init__(self):
        """Set defaults for optional fields and validate inputs."""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()
        if self.handoff_id is None:
            self.handoff_id = str(uuid.uuid4())
        if self.metadata is None:
            self.metadata = {}
        
        # Validate confidence bounds
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}")


class HandoffProtocol:
    """
    Protocol handler for standardized agent handoffs with serialization support.
    
    Provides methods for creating, validating, and serializing handoffs between
    agents in multi-agent systems. Supports multiple integration patterns and
    includes receipt generation for acknowledgment workflows.
    
    Examples:
        Basic handoff creation:
        >>> protocol = HandoffProtocol()
        >>> handoff = protocol.create_handoff("analyzer", "reporter", "Data processed", [])
        
        JSON serialization for REST APIs:
        >>> json_str = protocol.to_json(handoff)
        >>> restored_handoff = protocol.from_json(json_str)
        
        Receipt generation for acknowledgments:
        >>> receipt = protocol.generate_receipt(handoff, "received_and_processing")
    """
    
    def create_handoff(self, from_agent: str, to_agent: str, context_summary: str, 
                      artifacts: List[str], suggested_next_action: Optional[str] = None,
                      confidence: float = 1.0, metadata: Optional[Dict[str, Any]] = None) -> Handoff:
        """
        Create a new handoff with validation.
        
        Args:
            from_agent: Sending agent identifier
            to_agent: Receiving agent identifier  
            context_summary: Summary of current state and work done
            artifacts: List of work products (files, URLs, identifiers)
            suggested_next_action: Optional hint for next step
            confidence: Confidence score 0-1 (default: 1.0)
            metadata: Optional additional data
            
        Returns:
            Validated Handoff instance
            
        Examples:
            >>> protocol = HandoffProtocol()
            >>> handoff = protocol.create_handoff(
            ...     from_agent="data_collector",
            ...     to_agent="data_cleaner",
            ...     context_summary="Collected 1000 records from API",
            ...     artifacts=["raw_data/api_dump_20241108.json"],
            ...     suggested_next_action="remove_duplicates_and_validate",
            ...     confidence=0.95,
            ...     metadata={"source": "customer_api", "format": "json"}
            ... )
        """
        return Handoff(
            from_agent=from_agent,
            to_agent=to_agent,
            context_summary=context_summary,
            artifacts=artifacts,
            suggested_next_action=suggested_next_action,
            confidence=confidence,
            metadata=metadata or {}
        )
    
    def to_json(self, handoff: Handoff) -> str:
        """
        Serialize handoff to JSON string for network transfer.
        
        Args:
            handoff: Handoff instance to serialize
            
        Returns:
            JSON string representation
            
        Examples:
            >>> protocol = HandoffProtocol()
            >>> handoff = protocol.create_handoff("agent_a", "agent_b", "Task done", [])
            >>> json_data = protocol.to_json(handoff)
            >>> # Send via HTTP, message queue, etc.
        """
        return json.dumps(asdict(handoff), indent=2)
    
    def from_json(self, json_str: str) -> Handoff:
        """
        Deserialize handoff from JSON string.
        
        Args:
            json_str: JSON string to deserialize
            
        Returns:
            Handoff instance
            
        Examples:
            >>> protocol = HandoffProtocol()
            >>> json_data = '{"from_agent": "a", "to_agent": "b", ...}'
            >>> handoff = protocol.from_json(json_data)
        """
        data = json.loads(json_str)
        return Handoff(**data)
    
    def validate_handoff(self, handoff: Handoff) -> bool:
        """
        Validate handoff completeness and consistency.
        
        Args:
            handoff: Handoff to validate
            
        Returns:
            True if valid, raises ValueError if invalid
            
        Examples:
            >>> protocol = HandoffProtocol()
            >>> handoff = protocol.create_handoff("a", "b", "summary", [])
            >>> assert protocol.validate_handoff(handoff) == True
        """
        if not handoff.from_agent:
            raise ValueError("from_agent cannot be empty")
        if not handoff.to_agent:
            raise ValueError("to_agent cannot be empty")
        if not handoff.context_summary:
            raise ValueError("context_summary cannot be empty")
        if not isinstance(handoff.artifacts, list):
            raise ValueError("artifacts must be a list")
        if not 0 <= handoff.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        return True
    
    def generate_receipt(self, handoff: Handoff, status: str = "received") -> Dict[str, Any]:
        """
        Generate acknowledgment receipt for handoff tracking.
        
        Args:
            handoff: The handoff being acknowledged
            status: Status of the handoff (e.g., "received", "processing", "completed")
            
        Returns:
            Receipt dictionary with tracking information
            
        Examples:
            >>> protocol = HandoffProtocol()
            >>> handoff = protocol.create_handoff("researcher", "writer", "Done research", [])
            >>> receipt = protocol.generate_receipt(handoff, "received_and_processing")
            >>> # {'handoff_id': '...', 'status': 'received_and_processing', ...}
        """
        return {
            "handoff_id": handoff.handoff_id,
            "from_agent": handoff.from_agent,
            "to_agent": handoff.to_agent,
            "status": status,
            "received_at": datetime.utcnow().isoformat(),
            "original_timestamp": handoff.timestamp
        }