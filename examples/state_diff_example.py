#!/usr/bin/env python3
"""
Real example: Using StateDiff to track agent state changes

This example shows actual StateDiff usage with a simple agent that
processes a user query through multiple reasoning steps.
"""

from argentum import StateDiff
import time
import json


def simple_reasoning_agent(query: str):
    """A simple agent that processes queries with tracked state changes."""
    
    # Initialize state tracking
    diff = StateDiff()
    
    # Initial state
    state = {
        "query": query,
        "processed_tokens": [],
        "entities": [],
        "intent": None,
        "confidence": 0.0,
        "steps_completed": 0
    }
    
    diff.snapshot("start", state)
    print(f"📝 Processing query: '{query}'")
    
    # Step 1: Tokenization
    tokens = query.lower().split()
    state["processed_tokens"] = tokens
    state["steps_completed"] = 1
    
    diff.snapshot("tokenized", state)
    print(f"🔤 Tokenized: {tokens}")
    
    # Step 2: Entity extraction (simple keyword matching)
    entities = []
    entity_keywords = {
        "person": ["who", "person", "people", "human"],
        "location": ["where", "place", "city", "country"], 
        "time": ["when", "time", "date", "year"],
        "action": ["what", "how", "do", "make", "create"]
    }
    
    for token in tokens:
        for entity_type, keywords in entity_keywords.items():
            if token in keywords:
                entities.append({"type": entity_type, "value": token})
    
    state["entities"] = entities
    state["confidence"] = 0.3 if entities else 0.1
    state["steps_completed"] = 2
    
    diff.snapshot("entities_extracted", state)
    print(f"🏷️  Entities found: {entities}")
    
    # Step 3: Intent classification
    if any(e["type"] == "person" for e in entities):
        intent = "person_query"
    elif any(e["type"] == "location" for e in entities):
        intent = "location_query"
    elif any(e["type"] == "action" for e in entities):
        intent = "action_query"
    else:
        intent = "general_query"
    
    state["intent"] = intent
    state["confidence"] = min(state["confidence"] + 0.4, 1.0)
    state["steps_completed"] = 3
    
    diff.snapshot("intent_classified", state)
    print(f"🎯 Intent: {intent} (confidence: {state['confidence']:.2f})")
    
    return diff, state


def analyze_processing_changes(diff):
    """Analyze what changed during query processing."""
    print("\n" + "="*50)
    print("STATE CHANGE ANALYSIS")
    print("="*50)
    
    # Show each transition
    transitions = [
        ("start", "tokenized", "Tokenization"),
        ("tokenized", "entities_extracted", "Entity Extraction"), 
        ("entities_extracted", "intent_classified", "Intent Classification")
    ]
    
    for from_state, to_state, description in transitions:
        print(f"\n{description}:")
        changes = diff.get_changes(from_state, to_state)
        
        for field, change in changes.items():
            if "added" in change:
                print(f"  ➕ {field}: {change['added']}")
            elif "from" in change and "to" in change:
                print(f"  🔄 {field}: {change['from']} → {change['to']}")
    
    # Show sequential progression
    print(f"\n{'Sequential Changes:'}")
    sequence = diff.get_sequence_changes()
    for i, step in enumerate(sequence, 1):
        print(f"  {i}. {step['from']} → {step['to']}")
        key_changes = len([k for k in step['changes'].keys() if not k.startswith('steps_completed')])
        print(f"     {key_changes} meaningful changes")


def compare_different_queries():
    """Compare how different queries affect state evolution."""
    print("\n" + "="*50)
    print("QUERY COMPARISON")
    print("="*50)
    
    queries = [
        "Who is the president?",
        "Where is Paris located?", 
        "How do I make coffee?",
        "Tell me about quantum physics"
    ]
    
    results = []
    for query in queries:
        diff, final_state = simple_reasoning_agent(query)
        results.append((query, diff, final_state))
        print()
    
    # Compare final states
    print("Final State Comparison:")
    print("-" * 30)
    for query, diff, final_state in results:
        print(f"Query: {query}")
        print(f"  Intent: {final_state['intent']}")
        print(f"  Confidence: {final_state['confidence']:.2f}")
        print(f"  Entities: {len(final_state['entities'])}")
        print(f"  Tokens: {len(final_state['processed_tokens'])}")
        print()


def debug_confidence_drops():
    """Example of debugging unexpected confidence changes."""
    print("\n" + "="*50)
    print("DEBUGGING CONFIDENCE ISSUES")
    print("="*50)
    
    diff = StateDiff()
    
    # Simulate a problematic sequence where confidence unexpectedly drops
    state1 = {"confidence": 0.8, "reasoning": "strong_evidence", "facts": ["fact1", "fact2"]}
    state2 = {"confidence": 0.9, "reasoning": "additional_evidence", "facts": ["fact1", "fact2", "fact3"]}
    state3 = {"confidence": 0.4, "reasoning": "conflicting_evidence", "facts": ["fact1", "fact3"]}  # Lost fact2!
    
    diff.snapshot("high_confidence", state1)
    diff.snapshot("peak_confidence", state2) 
    diff.snapshot("confidence_drop", state3)
    
    # Analyze what caused the drop
    problematic_change = diff.get_changes("peak_confidence", "confidence_drop")
    
    print("🚨 Confidence drop detected!")
    print("Changes that occurred:")
    
    for field, change in problematic_change.items():
        if field == "confidence" and "from" in change and "to" in change:
            drop = change["from"] - change["to"]
            print(f"  📉 Confidence dropped by {drop:.1f} ({change['from']:.1f} → {change['to']:.1f})")
        elif "removed" in change:
            print(f"  ❌ Lost: {field} = {change['removed']}")
        elif "from" in change and "to" in change:
            print(f"  🔄 Changed: {field} = {change['from']} → {change['to']}")
    
    print("\n💡 Debugging insight: Confidence dropped when fact2 was lost")
    print("   Recommendation: Investigate fact validation logic")


def track_memory_evolution():
    """Track how agent memory evolves over multiple interactions."""
    print("\n" + "="*50)
    print("MEMORY EVOLUTION TRACKING")
    print("="*50)
    
    diff = StateDiff()
    
    # Simulate agent learning over time
    memory_states = [
        {"facts": [], "user_preferences": {}, "session_count": 0},
        {"facts": ["user likes coffee"], "user_preferences": {"beverage": "coffee"}, "session_count": 1},
        {"facts": ["user likes coffee", "user works remotely"], "user_preferences": {"beverage": "coffee", "work_style": "remote"}, "session_count": 2},
        {"facts": ["user likes coffee", "user works remotely", "user prefers morning meetings"], "user_preferences": {"beverage": "coffee", "work_style": "remote", "meeting_time": "morning"}, "session_count": 3},
    ]
    
    for i, state in enumerate(memory_states):
        diff.snapshot(f"session_{i}", state)
        if i > 0:
            print(f"Session {i}:")
            changes = diff.get_changes(f"session_{i-1}", f"session_{i}")
            
            for field, change in changes.items():
                if "added" in change:
                    if isinstance(change["added"], list):
                        for item in change["added"]:
                            print(f"  🧠 Learned: {item}")
                    elif isinstance(change["added"], dict):
                        for k, v in change["added"].items():
                            print(f"  📝 Preference: {k} = {v}")
                    else:
                        print(f"  ➕ Added: {field} = {change['added']}")
                elif "from" in change and "to" in change:
                    print(f"  📈 Updated: {field} = {change['to']}")
    
    # Show cumulative learning
    total_changes = diff.get_changes("session_0", f"session_{len(memory_states)-1}")
    print(f"\nCumulative learning over {len(memory_states)} sessions:")
    
    for field, change in total_changes.items():
        if "added" in change:
            if isinstance(change["added"], list):
                print(f"  🎓 Total facts learned: {len(change['added'])}")
            elif isinstance(change["added"], dict):
                print(f"  🎯 Preferences discovered: {len(change['added'])}")


def main():
    """Run all StateDiff examples with real data."""
    print("StateDiff Real Usage Examples")
    print("="*50)
    
    # Basic agent processing
    diff, final_state = simple_reasoning_agent("Who is the current president?")
    analyze_processing_changes(diff)
    
    # Compare different query types
    compare_different_queries()
    
    # Debug confidence issues
    debug_confidence_drops()
    
    # Track memory evolution
    track_memory_evolution()
    
    print("\n" + "="*50)
    print("💡 StateDiff Use Cases Demonstrated:")
    print("   ✅ Track processing pipeline changes")
    print("   ✅ Compare agent behavior across inputs")
    print("   ✅ Debug unexpected state transitions") 
    print("   ✅ Monitor long-term memory evolution")
    print("   ✅ Identify performance bottlenecks")
    print("   ✅ Validate agent reasoning consistency")


if __name__ == "__main__":
    main()