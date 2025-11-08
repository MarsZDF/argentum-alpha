#!/usr/bin/env python3
"""
Real example: Agent handoff protocols in a content creation pipeline

This demonstrates actual handoff usage between specialized agents
in a realistic content creation workflow.
"""

from argentum import Handoff, HandoffProtocol
import json
import time
from datetime import datetime


class ContentCreationPipeline:
    """A real content creation pipeline using agent handoffs."""
    
    def __init__(self):
        self.protocol = HandoffProtocol()
        self.agents = {
            "researcher": self.research_agent,
            "writer": self.writer_agent,
            "editor": self.editor_agent,
            "formatter": self.formatter_agent
        }
        self.artifacts = {}  # Simulated file system
    
    def research_agent(self, handoff_data):
        """Research agent: gathers information on a topic."""
        if handoff_data:
            topic = handoff_data.get("topic", "unknown topic")
        else:
            topic = "AI agents"
        
        print(f"🔍 Research Agent: Investigating '{topic}'")
        
        # Simulate research work
        research_data = {
            "topic": topic,
            "sources": [
                "https://arxiv.org/paper/ai-agents-2024",
                "https://blog.openai.com/agents", 
                "Research paper: 'Multi-Agent Systems in Practice'"
            ],
            "key_facts": [
                "AI agents can perform autonomous tasks",
                "Multi-agent systems enable specialization",
                "Agent coordination is a key challenge"
            ],
            "statistics": {
                "papers_reviewed": 15,
                "expert_opinions": 5,
                "case_studies": 3
            }
        }
        
        # Store artifacts
        research_file = f"research_{topic.replace(' ', '_')}.json"
        self.artifacts[research_file] = research_data
        
        # Create handoff to writer
        handoff = self.protocol.create_handoff(
            from_agent="researcher",
            to_agent="writer",
            context_summary=f"Completed research on '{topic}'. Found {len(research_data['key_facts'])} key insights from {research_data['statistics']['papers_reviewed']} sources.",
            artifacts=[research_file, f"sources_{topic.replace(' ', '_')}.txt"],
            suggested_next_action="create_first_draft",
            confidence=0.85,
            metadata={
                "topic": topic,
                "research_depth": "comprehensive",
                "source_quality": "high",
                "estimated_writing_time": "2 hours"
            }
        )
        
        print(f"  📄 Created artifacts: {handoff.artifacts}")
        print(f"  🎯 Confidence: {handoff.confidence}")
        return handoff
    
    def writer_agent(self, handoff):
        """Writer agent: creates content from research."""
        print(f"✍️  Writer Agent: Received handoff from {handoff.from_agent}")
        print(f"  📝 Context: {handoff.context_summary}")
        
        # Load research data
        research_file = handoff.artifacts[0]
        research_data = self.artifacts.get(research_file, {})
        
        # Simulate writing process
        draft_content = {
            "title": f"Understanding {research_data.get('topic', 'AI Agents')}",
            "introduction": "This article explores the rapidly evolving field of AI agents...",
            "main_sections": [
                "What are AI Agents?",
                "Key Capabilities and Use Cases", 
                "Challenges in Multi-Agent Systems",
                "Future Directions"
            ],
            "conclusion": "AI agents represent a significant advancement in autonomous systems...",
            "word_count": 1200,
            "references": research_data.get("sources", [])
        }
        
        # Store draft
        draft_file = f"draft_{research_data.get('topic', 'article').replace(' ', '_')}.md"
        self.artifacts[draft_file] = draft_content
        
        # Create handoff to editor
        handoff = self.protocol.create_handoff(
            from_agent="writer",
            to_agent="editor",
            context_summary=f"Completed first draft: {draft_content['word_count']} words, {len(draft_content['main_sections'])} sections. Ready for editorial review.",
            artifacts=[draft_file, research_file],  # Include original research
            suggested_next_action="structural_edit",
            confidence=0.75,  # Lower confidence, needs editing
            metadata={
                "word_count": draft_content["word_count"],
                "sections": len(draft_content["main_sections"]),
                "writing_style": "technical_informative",
                "target_audience": "developers"
            }
        )
        
        print(f"  📊 Draft: {draft_content['word_count']} words")
        print(f"  🎯 Confidence: {handoff.confidence}")
        return handoff
    
    def editor_agent(self, handoff):
        """Editor agent: reviews and improves content."""
        print(f"📝 Editor Agent: Received handoff from {handoff.from_agent}")
        print(f"  🔍 Context: {handoff.context_summary}")
        
        # Load draft
        draft_file = handoff.artifacts[0]
        draft_content = self.artifacts.get(draft_file, {})
        
        # Simulate editing process
        edited_content = draft_content.copy()
        edited_content.update({
            "title": "Understanding AI Agents: A Comprehensive Guide",  # Improved title
            "word_count": 1350,  # Expanded during editing
            "editorial_changes": [
                "Clarified technical terminology",
                "Added transition sentences",
                "Improved conclusion with actionable insights",
                "Added subheadings for better readability"
            ],
            "readability_score": 8.2,
            "technical_accuracy": "verified"
        })
        
        # Store edited version
        edited_file = f"edited_{draft_file}"
        self.artifacts[edited_file] = edited_content
        
        # Create handoff to formatter
        handoff = self.protocol.create_handoff(
            from_agent="editor",
            to_agent="formatter",
            context_summary=f"Editorial review complete. Improved structure and clarity. Word count: {edited_content['word_count']}. Ready for final formatting.",
            artifacts=[edited_file, draft_file],  # Include both versions
            suggested_next_action="apply_publication_format",
            confidence=0.92,  # High confidence after editing
            metadata={
                "readability_score": edited_content["readability_score"],
                "changes_made": len(edited_content["editorial_changes"]),
                "publication_ready": True,
                "target_format": "blog_post"
            }
        )
        
        print(f"  ✨ Improvements: {len(edited_content['editorial_changes'])} changes")
        print(f"  📊 Readability: {edited_content['readability_score']}/10")
        print(f"  🎯 Confidence: {handoff.confidence}")
        return handoff
    
    def formatter_agent(self, handoff):
        """Formatter agent: applies final formatting and publishing."""
        print(f"🎨 Formatter Agent: Received handoff from {handoff.from_agent}")
        print(f"  📄 Context: {handoff.context_summary}")
        
        # Load edited content
        edited_file = handoff.artifacts[0]
        edited_content = self.artifacts.get(edited_file, {})
        
        # Simulate formatting
        final_content = {
            "title": edited_content.get("title", "Article"),
            "formatted_content": "# " + edited_content.get("title", "Article") + "\n\n[Formatted content here...]",
            "metadata": {
                "author": "AI Content Pipeline",
                "publication_date": datetime.now().isoformat(),
                "tags": ["ai", "agents", "technology"],
                "estimated_read_time": f"{edited_content.get('word_count', 1000) // 200} min"
            },
            "seo_optimized": True,
            "accessibility_compliant": True,
            "format": "markdown_blog_post"
        }
        
        # Store final version
        final_file = f"published_{edited_file.replace('edited_', '')}"
        self.artifacts[final_file] = final_content
        
        print(f"  ✅ Published: {final_file}")
        print(f"  📱 SEO optimized: {final_content['seo_optimized']}")
        print(f"  ♿ Accessible: {final_content['accessibility_compliant']}")
        
        # Final handoff (could be to publishing system)
        handoff = self.protocol.create_handoff(
            from_agent="formatter",
            to_agent="publishing_system",
            context_summary=f"Content fully formatted and ready for publication. SEO optimized, accessibility compliant.",
            artifacts=[final_file],
            suggested_next_action="schedule_publication",
            confidence=0.95,
            metadata={
                "publication_ready": True,
                "format": final_content["format"],
                "estimated_engagement": "high"
            }
        )
        
        return handoff
    
    def run_pipeline(self, topic="AI agents in production"):
        """Run the complete content creation pipeline."""
        print("🚀 Starting Content Creation Pipeline")
        print("="*50)
        
        handoffs = []
        
        # Start with research
        current_handoff = self.research_agent({"topic": topic})
        handoffs.append(current_handoff)
        
        # Continue through pipeline
        while current_handoff.to_agent in self.agents:
            agent_func = self.agents[current_handoff.to_agent]
            current_handoff = agent_func(current_handoff)
            handoffs.append(current_handoff)
            
            # Generate receipt for tracking
            receipt = self.protocol.generate_receipt(current_handoff, "completed")
            print(f"  📋 Receipt: {receipt['handoff_id'][:8]}... ({receipt['status']})")
        
        return handoffs
    
    def analyze_handoff_chain(self, handoffs):
        """Analyze the effectiveness of the handoff chain."""
        print(f"\n{'='*50}")
        print("HANDOFF CHAIN ANALYSIS")
        print("="*50)
        
        print(f"Total handoffs: {len(handoffs)}")
        print(f"Pipeline path: {' → '.join([h.from_agent for h in handoffs] + [handoffs[-1].to_agent])}")
        
        # Confidence progression
        print(f"\nConfidence progression:")
        for i, handoff in enumerate(handoffs):
            print(f"  {i+1}. {handoff.from_agent} → {handoff.to_agent}: {handoff.confidence:.2f}")
        
        # Artifact flow
        print(f"\nArtifact flow:")
        all_artifacts = set()
        for handoff in handoffs:
            all_artifacts.update(handoff.artifacts)
        print(f"  Total artifacts created: {len(all_artifacts)}")
        print(f"  Artifacts: {list(all_artifacts)}")
        
        # Metadata analysis
        print(f"\nMetadata insights:")
        for handoff in handoffs:
            if handoff.metadata:
                key_metrics = {k: v for k, v in handoff.metadata.items() 
                             if k in ['word_count', 'readability_score', 'changes_made']}
                if key_metrics:
                    print(f"  {handoff.from_agent}: {key_metrics}")


def demonstrate_handoff_serialization():
    """Show how handoffs can be serialized for network transfer."""
    print(f"\n{'='*50}")
    print("HANDOFF SERIALIZATION DEMO")
    print("="*50)
    
    protocol = HandoffProtocol()
    
    # Create a handoff
    handoff = protocol.create_handoff(
        from_agent="data_processor",
        to_agent="ml_trainer",
        context_summary="Processed 10,000 samples, cleaned and normalized data",
        artifacts=["clean_data.csv", "feature_stats.json"],
        confidence=0.88,
        metadata={"samples": 10000, "features": 42, "quality_score": 0.93}
    )
    
    # Serialize to JSON
    json_data = protocol.to_json(handoff)
    print("📤 Serialized handoff:")
    print(json_data[:200] + "..." if len(json_data) > 200 else json_data)
    
    # Simulate network transfer (save/load)
    with open("/tmp/handoff.json", "w") as f:
        f.write(json_data)
    
    # Deserialize 
    with open("/tmp/handoff.json", "r") as f:
        loaded_json = f.read()
    
    restored_handoff = protocol.from_json(loaded_json)
    
    print(f"\n📥 Restored handoff:")
    print(f"  From: {restored_handoff.from_agent} → To: {restored_handoff.to_agent}")
    print(f"  Artifacts: {restored_handoff.artifacts}")
    print(f"  Confidence: {restored_handoff.confidence}")
    print(f"  ID matches: {handoff.handoff_id == restored_handoff.handoff_id}")


def demonstrate_error_handling():
    """Show handoff validation and error cases."""
    print(f"\n{'='*50}")
    print("HANDOFF ERROR HANDLING")
    print("="*50)
    
    protocol = HandoffProtocol()
    
    # Test validation
    try:
        valid_handoff = protocol.create_handoff(
            "agent_a", "agent_b", "Valid handoff", ["file.txt"], confidence=0.8
        )
        print("✅ Valid handoff created successfully")
        assert protocol.validate_handoff(valid_handoff)
        print("✅ Validation passed")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    # Test invalid confidence
    try:
        invalid_handoff = protocol.create_handoff(
            "agent_a", "agent_b", "Invalid confidence", [], confidence=1.5
        )
        print("❌ Should have failed with invalid confidence")
    except ValueError as e:
        print(f"✅ Correctly caught invalid confidence: {e}")
    
    # Test empty fields
    try:
        empty_handoff = Handoff("", "agent_b", "summary", [], 0.8)
        protocol.validate_handoff(empty_handoff)
        print("❌ Should have failed with empty from_agent")
    except ValueError as e:
        print(f"✅ Correctly caught empty field: {e}")


def main():
    """Run all handoff examples."""
    print("Handoff Protocol Real Usage Examples")
    print("="*60)
    
    # Run content creation pipeline
    pipeline = ContentCreationPipeline()
    handoffs = pipeline.run_pipeline("AI Agents in Production Systems")
    pipeline.analyze_handoff_chain(handoffs)
    
    # Show serialization
    demonstrate_handoff_serialization()
    
    # Show error handling
    demonstrate_error_handling()
    
    print(f"\n{'='*60}")
    print("💡 Handoff Protocol Use Cases Demonstrated:")
    print("   ✅ Multi-agent workflow coordination")
    print("   ✅ Context preservation across agent boundaries")
    print("   ✅ Artifact tracking and versioning")
    print("   ✅ Confidence monitoring through pipeline")
    print("   ✅ JSON serialization for distributed systems")
    print("   ✅ Validation and error handling")
    print("   ✅ Receipt generation for acknowledgments")


if __name__ == "__main__":
    main()