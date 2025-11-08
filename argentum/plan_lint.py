"""
Deterministic validation and linting for AI agent execution plans.

This module provides static analysis for agent-generated plans, catching errors
before expensive execution begins. It works like a traditional code linter but
for agent task plans, providing actionable feedback with error codes and fixes.

Why this matters:
- Catch errors before wasting API calls on partial execution
- Prevent security issues from exposed credentials
- Ensure plan correctness across different agent frameworks
- Enable CI/CD validation of agent behaviors

Example:
    >>> linter = PlanLinter()
    >>> result = linter.lint(
    ...     plan=agent_generated_plan,
    ...     tool_specs=available_tools,
    ...     secrets=["sk-", "api_key", "password"],
    ...     auto_fix=True
    ... )
    >>> 
    >>> if result.has_errors():
    ...     print(f"Found {len(result.issues)} issues:")
    ...     for issue in result.issues:
    ...         print(f"  {issue.code}: {issue.message} at {issue.location}")
    ...     
    ...     # Apply automatic fixes
    ...     fixed_plan = result.apply_patch(plan)
    ...     # Re-lint to ensure fixes worked
    ...     verify = linter.lint(fixed_plan, tool_specs)

Integration Use Cases:

1. Pre-execution validation:
   # Catch errors before running expensive operations
   plan = agent.create_plan(task)
   issues = linter.lint(plan, tools)
   if issues.has_errors():
       plan = agent.revise_plan(plan, issues)

2. Multi-agent plan validation:
   # Planner agent creates plan, executor validates before running
   handoff = receive_handoff()
   plan = handoff.artifacts["plan"]
   lint_result = linter.lint(plan, executor_tools)
   if lint_result.has_errors():
       return_to_planner(lint_result.issues)

3. Security scanning:
   # Prevent credential leaks
   secrets_patterns = ["sk-", "api_", "token", "password", "secret"]
   result = linter.lint(plan, tools, secrets=secrets_patterns)
   security_issues = [i for i in result.issues if i.code == "E004"]

4. Plan optimization:
   # Find inefficiencies
   result = linter.lint(plan, tools)
   duplicates = [i for i in result.issues if i.code == "W001"]
   unused = [i for i in result.issues if i.code == "W002"]
"""

import re
import json
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Set, Tuple
import difflib
from datetime import datetime


@dataclass
class Issue:
    """Represents a single linting issue in an agent execution plan."""
    code: str  # E001, W001, etc.
    severity: str  # "error" or "warning"
    message: str
    location: str  # "step2.tool", "step3.parameters.query"
    fix: Optional[str] = None  # Suggested automatic fix


class LintResult:
    """
    Container for plan linting results with actionable feedback.
    
    Provides methods for checking issue status, generating patches,
    and outputting in various formats for different integrations.
    
    Examples:
        >>> result = linter.lint(plan, tools)
        >>> if result.has_errors():
        ...     print(result)  # Human-readable output
        ...     sarif_data = result.to_sarif()  # CI/CD format
    """
    
    def __init__(self, issues: List[Issue]):
        self.issues = issues
        self._patches = []
    
    def has_errors(self) -> bool:
        """Return True if any issues are errors (severity='error')."""
        return any(issue.severity == "error" for issue in self.issues)
    
    def has_warnings(self) -> bool:
        """Return True if any issues are warnings (severity='warning')."""
        return any(issue.severity == "warning" for issue in self.issues)
    
    def to_sarif(self) -> Dict[str, Any]:
        """
        Export results in SARIF format for CI/CD integration.
        
        Returns:
            Dictionary in SARIF 2.1.0 format for GitHub Actions, etc.
        """
        rules = {}
        results = []
        
        for issue in self.issues:
            # Create rule definition
            if issue.code not in rules:
                rules[issue.code] = {
                    "id": issue.code,
                    "name": issue.code,
                    "shortDescription": {"text": issue.message.split(':')[0]},
                    "defaultConfiguration": {
                        "level": "error" if issue.severity == "error" else "warning"
                    }
                }
            
            # Create result
            results.append({
                "ruleId": issue.code,
                "level": issue.severity,
                "message": {"text": issue.message},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": "plan.json"},
                        "region": {"startLine": 1, "snippet": {"text": issue.location}}
                    }
                }]
            })
        
        return {
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "argentum-plan-lint",
                        "version": "1.0.0",
                        "rules": list(rules.values())
                    }
                },
                "results": results
            }]
        }
    
    def apply_patch(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply automatic fixes to the plan.
        
        Args:
            plan: Original plan dictionary
            
        Returns:
            Fixed plan with patches applied
            
        Note:
            Only applies fixes for issues that have fix suggestions.
        """
        import copy
        fixed_plan = copy.deepcopy(plan)
        
        for issue in self.issues:
            if issue.fix:
                self._apply_single_fix(fixed_plan, issue)
        
        return fixed_plan
    
    def _apply_single_fix(self, plan: Dict[str, Any], issue: Issue):
        """Apply a single fix to the plan (simplified implementation)."""
        if issue.code == "E001" and "did you mean" in issue.message:
            # Extract suggested tool name
            match = re.search(r"did you mean '([^']+)'\?", issue.message)
            if match:
                suggested_tool = match.group(1)
                step_id = issue.location.split('.')[0]
                
                for step in plan.get("steps", []):
                    if step.get("id") == step_id:
                        step["tool"] = suggested_tool
                        break
    
    def __str__(self) -> str:
        """Human-readable representation of linting results."""
        if not self.issues:
            return "✓ No issues found"
        
        lines = []
        for issue in self.issues:
            icon = "✗" if issue.severity == "error" else "⚠"
            lines.append(f"{icon} {issue.location}: {issue.code} {issue.message}")
        
        error_count = sum(1 for i in self.issues if i.severity == "error")
        warning_count = sum(1 for i in self.issues if i.severity == "warning")
        
        lines.append("")
        lines.append(f"Found {error_count} errors, {warning_count} warnings")
        
        if any(issue.fix for issue in self.issues):
            lines.append("Run with auto_fix=True to attempt automatic fixes")
        
        return "\n".join(lines)


class PlanLinter:
    """
    Validates AI agent execution plans for errors and security issues.
    
    Performs static analysis on agent-generated plans to catch common issues
    before execution begins, including invalid tool references, parameter
    errors, dependency problems, and potential security vulnerabilities.
    
    Examples:
        Basic usage:
        >>> linter = PlanLinter()
        >>> result = linter.lint(plan, tool_specs)
        >>> if result.has_errors():
        ...     print("Plan has errors:", result.issues)
        
        With security scanning:
        >>> result = linter.lint(plan, tools, secrets=["api_key", "token"])
        >>> security_issues = [i for i in result.issues if i.code == "E004"]
        
        With auto-fixing:
        >>> result = linter.lint(plan, tools, auto_fix=True)
        >>> if result.has_errors():
        ...     fixed_plan = result.apply_patch(plan)
    """
    
    def lint(self, plan: Dict[str, Any], tool_specs: Dict[str, Any], 
             secrets: Optional[List[str]] = None, auto_fix: bool = False) -> LintResult:
        """
        Lint an agent execution plan for errors and issues.
        
        Args:
            plan: Agent execution plan with 'steps' array
            tool_specs: Available tools with parameter specifications
            secrets: Optional list of secret patterns to detect
            auto_fix: Whether to generate automatic fix suggestions
            
        Returns:
            LintResult containing all detected issues
            
        Examples:
            >>> plan = {
            ...     "steps": [
            ...         {"id": "step1", "tool": "search_web", "parameters": {"query": "AI news"}},
            ...         {"id": "step2", "tool": "summarize", "parameters": {"text": "{step1.results}"}}
            ...     ]
            ... }
            >>> tools = {
            ...     "search_web": {"parameters": {"query": {"type": "string", "required": True}}},
            ...     "summarize": {"parameters": {"text": {"type": "string", "required": True}}}
            ... }
            >>> result = linter.lint(plan, tools)
        """
        issues = []
        
        if not isinstance(plan, dict) or "steps" not in plan:
            issues.append(Issue("E999", "error", "Invalid plan format: missing 'steps' array", "plan"))
            return LintResult(issues)
        
        steps = plan["steps"]
        step_outputs = {}  # Track what outputs are available
        step_dependencies = {}  # Track dependencies
        
        # First pass: collect outputs and dependencies
        for step in steps:
            step_id = step.get("id", "")
            step_outputs[step_id] = step.get("outputs", [])
            step_dependencies[step_id] = step.get("depends_on", [])
        
        # Second pass: validate each step
        for i, step in enumerate(steps):
            step_id = step.get("id", f"step{i+1}")
            
            # E001: Invalid tool reference
            tool_name = step.get("tool", "")
            if tool_name not in tool_specs:
                fix = self._suggest_tool_fix(tool_name, tool_specs) if auto_fix else None
                issues.append(Issue(
                    "E001", "error",
                    f"Tool '{tool_name}' not found" + (f" (did you mean '{fix}'?)" if fix else ""),
                    f"{step_id}.tool",
                    fix
                ))
                continue  # Skip further validation for this step
            
            # E002: Invalid parameters
            issues.extend(self._validate_parameters(step, tool_specs[tool_name], step_id, auto_fix))
            
            # E004: Secrets exposure
            if secrets:
                issues.extend(self._check_secrets(step, secrets, step_id))
        
        # E003: Dependency validation
        issues.extend(self._validate_dependencies(step_dependencies, steps))
        
        # W001: Duplicate steps
        issues.extend(self._check_duplicates(steps))
        
        # W002: Unused outputs
        issues.extend(self._check_unused_outputs(steps, step_outputs))
        
        return LintResult(issues)
    
    def _suggest_tool_fix(self, invalid_tool: str, tool_specs: Dict[str, Any]) -> Optional[str]:
        """Suggest closest matching tool name for typos."""
        matches = difflib.get_close_matches(invalid_tool, tool_specs.keys(), n=1, cutoff=0.6)
        return matches[0] if matches else None
    
    def _validate_parameters(self, step: Dict[str, Any], tool_spec: Dict[str, Any], 
                           step_id: str, auto_fix: bool) -> List[Issue]:
        """Validate step parameters against tool specification."""
        issues = []
        step_params = step.get("parameters", {})
        spec_params = tool_spec.get("parameters", {})
        
        # Check for invalid parameter names
        for param_name in step_params:
            if param_name not in spec_params:
                # Look for close matches
                matches = difflib.get_close_matches(param_name, spec_params.keys(), n=1, cutoff=0.6)
                suggestion = f" (did you mean '{matches[0]}'?)" if matches else ""
                issues.append(Issue(
                    "E002", "error",
                    f"Parameter '{param_name}' not valid for tool '{step.get('tool', '')}''{suggestion}",
                    f"{step_id}.parameters.{param_name}"
                ))
        
        # Check for missing required parameters
        for param_name, param_spec in spec_params.items():
            if param_spec.get("required", False) and param_name not in step_params:
                fix = f'{{REQUIRED: {param_name}}}' if auto_fix else None
                issues.append(Issue(
                    "E002", "error",
                    f"Missing required parameter '{param_name}'",
                    f"{step_id}.parameters",
                    fix
                ))
        
        return issues
    
    def _check_secrets(self, step: Dict[str, Any], secrets: List[str], step_id: str) -> List[Issue]:
        """Check for potential secrets in step parameters."""
        issues = []
        step_str = json.dumps(step.get("parameters", {}), default=str).lower()
        
        for secret_pattern in secrets:
            if secret_pattern.lower() in step_str:
                issues.append(Issue(
                    "E004", "error",
                    f"Potential secret '{secret_pattern}' exposed in parameters",
                    f"{step_id}.parameters"
                ))
        
        return issues
    
    def _validate_dependencies(self, dependencies: Dict[str, List[str]], 
                             steps: List[Dict[str, Any]]) -> List[Issue]:
        """Check for circular dependencies and invalid references."""
        issues = []
        step_ids = {step.get("id", f"step{i+1}") for i, step in enumerate(steps)}
        
        # Check for invalid dependency references
        for step_id, deps in dependencies.items():
            for dep in deps:
                if dep not in step_ids:
                    issues.append(Issue(
                        "E003", "error",
                        f"Dependency '{dep}' does not exist",
                        f"{step_id}.depends_on"
                    ))
        
        # Simple circular dependency detection
        def has_cycle(current: str, visited: Set[str], path: Set[str]) -> bool:
            if current in path:
                return True
            if current in visited:
                return False
            
            visited.add(current)
            path.add(current)
            
            for dep in dependencies.get(current, []):
                if has_cycle(dep, visited, path):
                    return True
            
            path.remove(current)
            return False
        
        visited = set()
        for step_id in dependencies:
            if step_id not in visited and has_cycle(step_id, visited, set()):
                issues.append(Issue(
                    "E003", "error",
                    f"Circular dependency detected involving '{step_id}'",
                    f"{step_id}.depends_on"
                ))
        
        return issues
    
    def _check_duplicates(self, steps: List[Dict[str, Any]]) -> List[Issue]:
        """Check for duplicate step calls with same parameters."""
        issues = []
        seen = {}
        
        for i, step in enumerate(steps):
            step_id = step.get("id", f"step{i+1}")
            tool = step.get("tool", "")
            params = json.dumps(step.get("parameters", {}), sort_keys=True)
            signature = f"{tool}:{params}"
            
            if signature in seen:
                issues.append(Issue(
                    "W001", "warning",
                    f"Duplicate call to '{tool}' with same parameters (see {seen[signature]})",
                    step_id
                ))
            else:
                seen[signature] = step_id
        
        return issues
    
    def _check_unused_outputs(self, steps: List[Dict[str, Any]], 
                            step_outputs: Dict[str, List[str]]) -> List[Issue]:
        """Check for step outputs that are never referenced."""
        issues = []
        
        # Collect all parameter references
        all_params_text = ""
        for step in steps:
            all_params_text += json.dumps(step.get("parameters", {}), default=str)
        
        # Check each output
        for step_id, outputs in step_outputs.items():
            for output in outputs:
                # Look for common reference patterns: {step1.output}, ${step1.output}, {{step1.output}}
                patterns = [
                    f"{{{step_id}.{output}}}",
                    f"${{{step_id}.{output}}}",
                    f"{{{{{step_id}.{output}}}}}"
                ]
                
                if not any(pattern in all_params_text for pattern in patterns):
                    issues.append(Issue(
                        "W002", "warning",
                        f"Output '{output}' is never referenced",
                        f"{step_id}.outputs"
                    ))
        
        return issues