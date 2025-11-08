"""
Comprehensive tests for argentum.plan_lint module.

Tests validate deterministic linting rules for agent execution plans,
ensuring error detection, auto-fix suggestions, and security scanning work
correctly across various real-world scenarios.
"""

import pytest
from argentum.plan_lint import PlanLinter, Issue, LintResult


class TestPlanLinter:
    """Test plan linting functionality for agent execution validation."""
    
    def setup_method(self):
        """Setup common test data for each test."""
        self.linter = PlanLinter()
        
        # Standard tool specifications
        self.tool_specs = {
            "search_web": {
                "parameters": {
                    "query": {"type": "string", "required": True},
                    "max_results": {"type": "integer", "required": False, "default": 10}
                }
            },
            "summarize": {
                "parameters": {
                    "text": {"type": "string", "required": True},
                    "max_length": {"type": "integer", "required": False}
                }
            },
            "send_email": {
                "parameters": {
                    "to": {"type": "string", "required": True},
                    "subject": {"type": "string", "required": True},
                    "body": {"type": "string", "required": True}
                }
            },
            "analyze_data": {
                "parameters": {
                    "data": {"type": "string", "required": True},
                    "method": {"type": "string", "required": False, "default": "statistical"}
                }
            }
        }
    
    def test_e001_invalid_tool_reference(self):
        """
        Test E001: Detection of invalid tool references with suggestions.
        
        Validates that the linter catches typos in tool names and provides
        helpful suggestions for common misspellings.
        """
        plan = {
            "steps": [
                {
                    "id": "step1",
                    "tool": "search_webb",  # Typo: should be search_web
                    "parameters": {"query": "AI news"}
                }
            ]
        }
        
        result = self.linter.lint(plan, self.tool_specs, auto_fix=True)
        
        assert result.has_errors()
        assert len(result.issues) == 1
        
        issue = result.issues[0]
        assert issue.code == "E001"
        assert issue.severity == "error"
        assert "search_webb" in issue.message
        assert "did you mean 'search_web'" in issue.message
        assert issue.location == "step1.tool"
    
    def test_e001_completely_invalid_tool(self):
        """
        Test E001: Tools with no close matches.
        
        Validates handling of completely invalid tool names where
        no reasonable suggestion can be provided.
        """
        plan = {
            "steps": [
                {
                    "id": "step1", 
                    "tool": "xyz_invalid_tool",
                    "parameters": {}
                }
            ]
        }
        
        result = self.linter.lint(plan, self.tool_specs)
        
        assert result.has_errors()
        issue = result.issues[0]
        assert issue.code == "E001"
        assert "xyz_invalid_tool" in issue.message
        assert "did you mean" not in issue.message  # No close match
    
    def test_e002_invalid_parameter_names(self):
        """
        Test E002: Detection of invalid parameter names with suggestions.
        
        Validates parameter validation against tool specifications,
        including typo detection for parameter names.
        """
        plan = {
            "steps": [
                {
                    "id": "step1",
                    "tool": "search_web",
                    "parameters": {
                        "querry": "AI news",  # Typo: should be 'query'
                        "limit": 5  # Wrong param: should be 'max_results'
                    }
                }
            ]
        }
        
        result = self.linter.lint(plan, self.tool_specs)
        
        assert result.has_errors()
        assert len(result.issues) >= 2
        
        # Check for parameter name issues
        param_issues = [i for i in result.issues if i.code == "E002"]
        assert len(param_issues) >= 2
        
        # Should catch both 'querry' and 'limit' as invalid
        messages = [issue.message for issue in param_issues]
        assert any("querry" in msg and "did you mean 'query'" in msg for msg in messages)
        assert any("limit" in msg for msg in messages)
    
    def test_e002_missing_required_parameters(self):
        """
        Test E002: Detection of missing required parameters.
        
        Validates that linter catches missing required parameters
        and suggests fixes when auto_fix is enabled.
        """
        plan = {
            "steps": [
                {
                    "id": "step1",
                    "tool": "search_web",
                    "parameters": {
                        "max_results": 10  # Missing required 'query' parameter
                    }
                }
            ]
        }
        
        result = self.linter.lint(plan, self.tool_specs, auto_fix=True)
        
        assert result.has_errors()
        
        missing_param_issue = next(i for i in result.issues if "Missing required parameter 'query'" in i.message)
        assert missing_param_issue.code == "E002"
        assert missing_param_issue.fix is not None  # Auto-fix suggestion provided
    
    def test_e003_dependency_errors(self):
        """
        Test E003: Detection of dependency issues.
        
        Validates detection of circular dependencies and references
        to non-existent steps.
        """
        # Test circular dependency
        circular_plan = {
            "steps": [
                {
                    "id": "step1", 
                    "tool": "search_web",
                    "parameters": {"query": "test"},
                    "depends_on": ["step2"]
                },
                {
                    "id": "step2",
                    "tool": "summarize", 
                    "parameters": {"text": "test"},
                    "depends_on": ["step1"]  # Circular dependency
                }
            ]
        }
        
        result = self.linter.lint(circular_plan, self.tool_specs)
        
        assert result.has_errors()
        circular_issues = [i for i in result.issues if i.code == "E003" and "Circular dependency" in i.message]
        assert len(circular_issues) > 0
        
        # Test invalid dependency reference
        invalid_dep_plan = {
            "steps": [
                {
                    "id": "step1",
                    "tool": "search_web", 
                    "parameters": {"query": "test"},
                    "depends_on": ["step_nonexistent"]
                }
            ]
        }
        
        result = self.linter.lint(invalid_dep_plan, self.tool_specs)
        
        assert result.has_errors()
        invalid_dep_issues = [i for i in result.issues if "does not exist" in i.message]
        assert len(invalid_dep_issues) == 1
    
    def test_e004_secrets_exposure(self):
        """
        Test E004: Detection of potential secrets in parameters.
        
        Validates security scanning for common secret patterns
        in plan parameters to prevent credential leaks.
        """
        plan = {
            "steps": [
                {
                    "id": "step1",
                    "tool": "send_email",
                    "parameters": {
                        "to": "user@example.com",
                        "subject": "Test", 
                        "body": "Message",
                        "api_key": "sk-1234567890abcdef"  # Secret in parameters
                    }
                }
            ]
        }
        
        secrets = ["api_key", "sk-", "password", "token"]
        result = self.linter.lint(plan, self.tool_specs, secrets=secrets)
        
        assert result.has_errors()
        
        secret_issues = [i for i in result.issues if i.code == "E004"]
        assert len(secret_issues) >= 1  # Should catch api_key and/or sk-
        
        # Verify the issue points to the right location
        api_key_issue = next(i for i in secret_issues if "api_key" in i.message)
        assert "step1.parameters" in api_key_issue.location
    
    def test_w001_duplicate_steps(self):
        """
        Test W001: Detection of duplicate step calls.
        
        Validates identification of steps that call the same tool
        with identical parameters, indicating potential inefficiency.
        """
        plan = {
            "steps": [
                {
                    "id": "step1",
                    "tool": "search_web",
                    "parameters": {"query": "AI news", "max_results": 10}
                },
                {
                    "id": "step2", 
                    "tool": "search_web",
                    "parameters": {"query": "AI news", "max_results": 10}  # Duplicate
                },
                {
                    "id": "step3",
                    "tool": "search_web", 
                    "parameters": {"query": "Different query"}  # Not duplicate
                }
            ]
        }
        
        result = self.linter.lint(plan, self.tool_specs)
        
        assert result.has_warnings()
        
        duplicate_issues = [i for i in result.issues if i.code == "W001"]
        assert len(duplicate_issues) == 1
        
        issue = duplicate_issues[0]
        assert "step2" in issue.location
        assert "see step1" in issue.message
    
    def test_w002_unused_outputs(self):
        """
        Test W002: Detection of unused step outputs.
        
        Validates identification of steps that produce outputs
        which are never referenced by subsequent steps.
        """
        plan = {
            "steps": [
                {
                    "id": "step1",
                    "tool": "search_web",
                    "parameters": {"query": "AI news"},
                    "outputs": ["search_results", "unused_data"]  # unused_data never referenced
                },
                {
                    "id": "step2",
                    "tool": "summarize",
                    "parameters": {"text": "{step1.search_results}"}  # Only uses search_results
                }
            ]
        }
        
        result = self.linter.lint(plan, self.tool_specs)
        
        assert result.has_warnings()
        
        unused_issues = [i for i in result.issues if i.code == "W002"]
        assert len(unused_issues) == 1
        
        issue = unused_issues[0]
        assert "unused_data" in issue.message
        assert "step1.outputs" in issue.location
    
    def test_auto_fix_functionality(self):
        """
        Test automatic fix generation and application.
        
        Validates that auto-fix suggestions are generated for
        common errors and can be applied to correct plans.
        """
        plan = {
            "steps": [
                {
                    "id": "step1",
                    "tool": "summerize",  # Typo: should be 'summarize'
                    "parameters": {"text": "Some text"}
                }
            ]
        }
        
        result = self.linter.lint(plan, self.tool_specs, auto_fix=True)
        
        assert result.has_errors()
        
        # Apply fixes
        fixed_plan = result.apply_patch(plan)
        
        # Verify fix was applied
        assert fixed_plan["steps"][0]["tool"] == "summarize"
        
        # Re-lint to ensure fix worked
        recheck = self.linter.lint(fixed_plan, self.tool_specs)
        tool_errors = [i for i in recheck.issues if i.code == "E001"]
        assert len(tool_errors) == 0  # Tool error should be fixed
    
    def test_complex_rag_pipeline(self):
        """
        Test realistic RAG pipeline plan validation.
        
        Validates linting of a complex multi-step plan representing
        a typical Retrieval-Augmented Generation workflow.
        """
        rag_tools = {
            "vector_search": {
                "parameters": {
                    "query": {"type": "string", "required": True},
                    "top_k": {"type": "integer", "required": False, "default": 5}
                }
            },
            "extract_text": {
                "parameters": {
                    "documents": {"type": "array", "required": True}
                }
            },
            "generate_response": {
                "parameters": {
                    "context": {"type": "string", "required": True},
                    "question": {"type": "string", "required": True}
                }
            },
            "format_output": {
                "parameters": {
                    "response": {"type": "string", "required": True},
                    "format": {"type": "string", "required": False, "default": "markdown"}
                }
            }
        }
        
        rag_plan = {
            "steps": [
                {
                    "id": "retrieve",
                    "tool": "vector_search", 
                    "parameters": {"query": "What is machine learning?", "top_k": 3},
                    "outputs": ["relevant_docs"]
                },
                {
                    "id": "extract",
                    "tool": "extract_text",
                    "parameters": {"documents": "{retrieve.relevant_docs}"},
                    "depends_on": ["retrieve"],
                    "outputs": ["extracted_text"]
                },
                {
                    "id": "generate",
                    "tool": "generate_response",
                    "parameters": {
                        "context": "{extract.extracted_text}",
                        "question": "What is machine learning?"
                    },
                    "depends_on": ["extract"],
                    "outputs": ["raw_response"]
                },
                {
                    "id": "format",
                    "tool": "format_output",
                    "parameters": {"response": "{generate.raw_response}"},
                    "depends_on": ["generate"]
                }
            ]
        }
        
        result = self.linter.lint(rag_plan, rag_tools)
        
        # Should have minimal issues for a well-formed plan
        assert not result.has_errors()
        
        # Might have minor warnings but no critical errors
        if result.has_warnings():
            warning_codes = [issue.code for issue in result.issues]
            assert all(code.startswith("W") for code in warning_codes)
    
    def test_sarif_output_format(self):
        """
        Test SARIF format output for CI/CD integration.
        
        Validates that linting results can be exported in SARIF format
        for integration with GitHub Actions and other CI/CD tools.
        """
        plan = {
            "steps": [
                {
                    "id": "step1",
                    "tool": "invalid_tool",
                    "parameters": {"invalid_param": "value"}
                }
            ]
        }
        
        result = self.linter.lint(plan, self.tool_specs)
        sarif_data = result.to_sarif()
        
        # Validate SARIF structure
        assert sarif_data["$schema"] == "https://json.schemastore.org/sarif-2.1.0.json"
        assert sarif_data["version"] == "2.1.0"
        assert "runs" in sarif_data
        assert len(sarif_data["runs"]) == 1
        
        run = sarif_data["runs"][0]
        assert "tool" in run
        assert run["tool"]["driver"]["name"] == "argentum-plan-lint"
        assert "results" in run
        assert len(run["results"]) > 0
        
        # Validate result structure
        for result_item in run["results"]:
            assert "ruleId" in result_item
            assert "level" in result_item
            assert "message" in result_item
    
    def test_edge_cases_and_malformed_plans(self):
        """
        Test handling of edge cases and malformed plan structures.
        
        Validates robust error handling for invalid input that might
        be produced by faulty agents or corrupted data.
        """
        # Empty plan
        empty_result = self.linter.lint({}, self.tool_specs)
        assert empty_result.has_errors()
        assert any("missing 'steps'" in issue.message for issue in empty_result.issues)
        
        # Plan with no steps array
        no_steps_result = self.linter.lint({"other_field": "value"}, self.tool_specs)
        assert no_steps_result.has_errors()
        
        # Plan with empty steps
        empty_steps_result = self.linter.lint({"steps": []}, self.tool_specs)
        assert not empty_steps_result.has_errors()  # Empty is valid
        
        # Plan with malformed step
        malformed_plan = {
            "steps": [
                {
                    "id": "step1",
                    # Missing 'tool' field
                    "parameters": {"query": "test"}
                }
            ]
        }
        
        malformed_result = self.linter.lint(malformed_plan, self.tool_specs)
        assert malformed_result.has_errors()
    
    def test_human_readable_output(self):
        """
        Test human-readable string representation of results.
        
        Validates that linting results can be formatted for
        command-line tools and developer-friendly output.
        """
        plan = {
            "steps": [
                {
                    "id": "step1",
                    "tool": "search_webb",  # Error
                    "parameters": {"query": "test"}
                },
                {
                    "id": "step2", 
                    "tool": "search_web",  # Should create duplicate warning
                    "parameters": {"query": "test"},
                    "outputs": ["unused_output"]  # Should create unused output warning
                },
                {
                    "id": "step3", 
                    "tool": "search_web",  # Duplicate of step2
                    "parameters": {"query": "test"}
                }
            ]
        }
        
        result = self.linter.lint(plan, self.tool_specs, auto_fix=True)
        output_str = str(result)
        
        # Should contain both error and warning indicators
        assert "✗" in output_str  # Error symbol
        assert "⚠" in output_str  # Warning symbol
        
        # Should contain issue codes and locations
        assert "E001" in output_str
        assert "step1.tool" in output_str
        
        # Should contain summary
        assert "Found" in output_str
        assert "errors" in output_str
        assert "warnings" in output_str
        
        # Should mention auto-fix availability
        assert "auto_fix=True" in output_str
    
    def test_lint_result_utility_methods(self):
        """
        Test LintResult utility methods for issue categorization.
        
        Validates helper methods for checking error/warning status
        and processing results programmatically.
        """
        issues = [
            Issue("E001", "error", "Error message", "step1.tool"),
            Issue("W001", "warning", "Warning message", "step2")
        ]
        result = LintResult(issues)
        
        assert result.has_errors() == True
        assert result.has_warnings() == True
        
        # Test with no errors
        warning_only_result = LintResult([issues[1]])
        assert warning_only_result.has_errors() == False
        assert warning_only_result.has_warnings() == True
        
        # Test empty result
        empty_result = LintResult([])
        assert empty_result.has_errors() == False
        assert empty_result.has_warnings() == False