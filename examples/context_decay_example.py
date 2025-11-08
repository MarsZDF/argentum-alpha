#!/usr/bin/env python3
"""
Real example: Context decay in a conversational AI assistant

This demonstrates actual ContextDecay usage in a realistic chatbot
scenario where user preferences and conversation context naturally fade over time.
"""

from argentum import ContextDecay
import time
import random


class ConversationalAgent:
    """A chatbot that uses context decay for memory management."""
    
    def __init__(self, memory_half_life=10):
        self.context = ContextDecay(half_life_steps=memory_half_life)
        self.conversation_turn = 0
        self.user_id = "user_123"
        
    def process_user_message(self, message, user_metadata=None):
        """Process a user message and update context."""
        self.conversation_turn += 1
        
        print(f"\nTurn {self.conversation_turn}: User says: '{message}'")
        
        # Extract and store context from this message
        self._extract_context(message, user_metadata or {})
        
        # Advance time (simulate conversation progression)
        self.context.step()
        
        # Generate response based on current context
        response = self._generate_response(message)
        
        print(f"Bot: {response}")
        return response
    
    def _extract_context(self, message, metadata):
        """Extract contextual information from user message."""
        message_lower = message.lower()
        
        # Extract user preferences
        if "i like" in message_lower or "i prefer" in message_lower:
            # Simple preference extraction
            if "coffee" in message_lower:
                self.context.add("beverage_preference", "coffee", importance=0.8)
            elif "tea" in message_lower:
                self.context.add("beverage_preference", "tea", importance=0.8)
            elif "formal" in message_lower:
                self.context.add("tone_preference", "formal", importance=0.7)
            elif "casual" in message_lower:
                self.context.add("tone_preference", "casual", importance=0.7)
        
        # Extract personal information
        if "my name is" in message_lower:
            name = message_lower.split("my name is")[-1].strip().split()[0]
            self.context.add("user_name", name, importance=0.9)
        
        # Extract current task/intent
        if any(word in message_lower for word in ["help", "need", "want", "how"]):
            if "schedule" in message_lower or "calendar" in message_lower:
                self.context.add("current_task", "scheduling", importance=1.0)
            elif "recipe" in message_lower or "cook" in message_lower:
                self.context.add("current_task", "cooking", importance=1.0)
            elif "weather" in message_lower:
                self.context.add("current_task", "weather_query", importance=1.0)
            elif "email" in message_lower:
                self.context.add("current_task", "email_assistance", importance=1.0)
        
        # Store conversation metadata
        self.context.add("last_message_length", len(message), importance=0.3)
        self.context.add("conversation_turn", self.conversation_turn, importance=0.4)
        
        # Add metadata if provided
        for key, value in metadata.items():
            self.context.add(f"metadata_{key}", value, importance=0.5)
    
    def _generate_response(self, message):
        """Generate response based on current active context."""
        
        # Get active context (above decay threshold)
        active_context = self.context.get_active(threshold=0.4)
        
        # Build response based on what we remember
        context_dict = {key: value for key, value, weight in active_context}
        
        # Personalize based on remembered name
        greeting = ""
        if "user_name" in context_dict:
            greeting = f"Hi {context_dict['user_name']}, "
        
        # Respond based on current task
        if "current_task" in context_dict:
            task = context_dict["current_task"]
            if task == "scheduling":
                response = f"{greeting}I can help you with scheduling. "
            elif task == "cooking":
                response = f"{greeting}I'd be happy to help with cooking! "
            elif task == "weather_query":
                response = f"{greeting}Let me check the weather for you. "
            elif task == "email_assistance":
                response = f"{greeting}I can assist with your email. "
            else:
                response = f"{greeting}I'm here to help. "
        else:
            response = f"{greeting}How can I assist you today? "
        
        # Add preference-based personalization
        if "tone_preference" in context_dict:
            if context_dict["tone_preference"] == "formal":
                response = response.replace("Hi", "Hello").replace("I'd", "I would")
            # Casual tone is default
        
        if "beverage_preference" in context_dict:
            beverage = context_dict["beverage_preference"]
            response += f"(By the way, would you like me to remind you about {beverage} break times?) "
        
        return response.strip()
    
    def show_memory_state(self):
        """Display current memory state and decay statistics."""
        stats = self.context.get_stats()
        active_items = self.context.get_active(threshold=0.3)
        
        print(f"\n🧠 Memory State (Turn {self.conversation_turn}):")
        print(f"   Total items: {stats['total_items']}")
        print(f"   Active items: {stats['active_items']}")
        print(f"   Average decay: {stats['avg_decay']:.2f}")
        print(f"   Oldest item age: {stats['oldest_age']} turns")
        
        if active_items:
            print(f"   Active context:")
            for key, value, weight in active_items[:5]:  # Show top 5
                print(f"     {key}: {value} (weight: {weight:.2f})")
    
    def simulate_memory_cleanup(self):
        """Demonstrate automatic memory cleanup."""
        before_count = self.context.get_stats()['total_items']
        removed = self.context.clear_expired(threshold=0.1)
        after_count = self.context.get_stats()['total_items']
        
        if removed > 0:
            print(f"🧹 Cleaned up {removed} expired memories ({before_count} → {after_count} items)")


def simulate_long_conversation():
    """Simulate a longer conversation showing memory decay."""
    print("Simulating Long Conversation with Memory Decay")
    print("="*50)
    
    agent = ConversationalAgent(memory_half_life=8)
    
    # Conversation sequence
    conversation = [
        ("Hi, my name is Alice and I prefer casual conversations", {"session_start": True}),
        ("I like coffee a lot", {}),
        ("Can you help me schedule a meeting?", {}),
        ("Actually, let me check the weather first", {}),
        ("What's the temperature today?", {}),
        ("Thanks! Now back to scheduling that meeting", {}),
        ("I need to schedule it for tomorrow morning", {}),
        ("Perfect, that works for me", {}),
        ("By the way, do you remember what I like to drink?", {}),
        ("I also like tea now", {}),  # Changing preference
        ("Can you help me write an email?", {}),  # New task
        ("The email is about the meeting we just scheduled", {}),
        ("Actually, I prefer more formal communication for work emails", {}),  # Changing tone
        ("Thanks for all your help today!", {}),
        ("Oh wait, what was my name again?", {}),  # Test if name is remembered
    ]
    
    for i, (message, metadata) in enumerate(conversation):
        agent.process_user_message(message, metadata)
        
        # Show memory state every few turns
        if i % 4 == 0 or i == len(conversation) - 1:
            agent.show_memory_state()
        
        # Simulate memory cleanup
        if i % 6 == 5:
            agent.simulate_memory_cleanup()
        
        time.sleep(0.1)  # Brief pause for readability


def demonstrate_different_decay_rates():
    """Show how different decay rates affect memory retention."""
    print(f"\n{'='*50}")
    print("COMPARING DIFFERENT DECAY RATES")
    print("="*50)
    
    # Create agents with different memory spans
    agents = {
        "short_memory": ConversationalAgent(memory_half_life=3),
        "medium_memory": ConversationalAgent(memory_half_life=8), 
        "long_memory": ConversationalAgent(memory_half_life=15)
    }
    
    # Add same initial context to all
    for agent in agents.values():
        agent.context.add("user_name", "Bob", importance=0.9)
        agent.context.add("beverage_preference", "coffee", importance=0.8)
        agent.context.add("project", "website_redesign", importance=0.7)
    
    # Advance time for all agents
    turns = 12
    for turn in range(turns):
        for agent in agents.values():
            agent.context.step()
    
    # Compare what each agent remembers
    print(f"After {turns} conversation turns:")
    
    for name, agent in agents.items():
        active_context = agent.context.get_active(threshold=0.3)
        print(f"\n{name.replace('_', ' ').title()} Agent:")
        
        if active_context:
            for key, value, weight in active_context:
                print(f"  {key}: {value} (weight: {weight:.2f})")
        else:
            print("  No active context remembered")


def demonstrate_custom_importance():
    """Show how importance affects decay resistance."""
    print(f"\n{'='*50}")
    print("IMPORTANCE-BASED DECAY RESISTANCE")
    print("="*50)
    
    agent = ConversationalAgent(memory_half_life=5)
    
    # Add context with different importance levels
    contexts = [
        ("critical_deadline", "Project due Friday", 1.0),
        ("user_name", "Charlie", 0.9),
        ("beverage_preference", "green tea", 0.6),
        ("weather_comment", "It's sunny today", 0.3),
        ("random_fact", "Python was created in 1991", 0.1)
    ]
    
    for key, value, importance in contexts:
        agent.context.add(key, value, importance=importance)
    
    print("Initial context (with importance scores):")
    for key, value, importance in contexts:
        print(f"  {key}: {value} (importance: {importance})")
    
    # Advance time and show what survives
    print(f"\nAfter decay progression:")
    
    for step in [3, 6, 10, 15]:
        # Advance to this step
        while agent.context.current_step < step:
            agent.context.step()
        
        active = agent.context.get_active(threshold=0.2)
        print(f"\nStep {step}:")
        
        if active:
            for key, value, weight in active:
                original_importance = next(imp for k, v, imp in contexts if k == key)
                print(f"  {key}: {value} (weight: {weight:.2f}, was: {original_importance})")
        else:
            print("  All context has decayed below threshold")


def analyze_memory_patterns():
    """Analyze memory usage patterns over time."""
    print(f"\n{'='*50}")
    print("MEMORY USAGE PATTERN ANALYSIS")
    print("="*50)
    
    agent = ConversationalAgent(memory_half_life=6)
    
    # Simulate adding different types of context over time
    memory_stats = []
    
    for turn in range(20):
        # Randomly add different types of context
        if turn % 3 == 0:
            agent.context.add(f"fact_{turn}", f"learned fact {turn}", importance=random.uniform(0.3, 0.8))
        
        if turn % 4 == 0:
            agent.context.add("current_topic", f"topic_{turn//4}", importance=0.9)
        
        if turn % 7 == 0:
            agent.context.add("user_preference", f"pref_{turn}", importance=0.7)
        
        agent.context.step()
        
        # Record statistics
        stats = agent.context.get_stats()
        memory_stats.append((turn, stats))
        
        # Periodic cleanup
        if turn % 8 == 7:
            agent.context.clear_expired(threshold=0.15)
    
    # Analyze patterns
    print("Memory usage over time:")
    print("Turn | Total | Active | Avg Decay | Oldest")
    print("-" * 45)
    
    for turn, stats in memory_stats[::3]:  # Show every 3rd turn
        print(f"{turn:4d} | {stats['total_items']:5d} | {stats['active_items']:6d} | "
              f"{stats['avg_decay']:8.2f} | {stats['oldest_age']:6d}")
    
    # Final memory state
    final_active = agent.context.get_active(threshold=0.3)
    print(f"\nFinal active memories ({len(final_active)} items):")
    for key, value, weight in final_active:
        print(f"  {key}: {str(value)[:20]}{'...' if len(str(value)) > 20 else ''} (weight: {weight:.2f})")


def main():
    """Run all context decay examples."""
    print("Context Decay Real Usage Examples")
    print("="*60)
    
    # Long conversation simulation
    simulate_long_conversation()
    
    # Compare decay rates
    demonstrate_different_decay_rates()
    
    # Show importance effects
    demonstrate_custom_importance()
    
    # Analyze patterns
    analyze_memory_patterns()
    
    print(f"\n{'='*60}")
    print("💡 Context Decay Use Cases Demonstrated:")
    print("   ✅ Natural conversation memory management")
    print("   ✅ User preference tracking with temporal relevance")
    print("   ✅ Automatic cleanup of stale information")
    print("   ✅ Importance-based retention priorities")
    print("   ✅ Memory usage optimization")
    print("   ✅ Long-term vs short-term memory simulation")


if __name__ == "__main__":
    main()