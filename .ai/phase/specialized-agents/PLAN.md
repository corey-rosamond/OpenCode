# Specialized Task Agents: Implementation Plan

**Phase:** specialized-agents
**Version Target:** 1.6.0
**Created:** 2025-12-21
**Updated:** 2025-12-21

---

## Overview

Extend Code-Forge's agent system with 16 new specialized agents covering diverse software development workflows. The current system has 4 agent types (explore, plan, code-review, general). This phase adds agents for coding, writing, security, research, testing, and project management.

**Current State:**
- Agent system exists in `src/code_forge/agents/`
- Base classes: `Agent` (ABC), `AgentState`, `ResourceLimits`, `AgentConfig`
- Registry: `AgentTypeRegistry` (Singleton, thread-safe)
- Existing types: explore, plan, code-review, general
- Factory pattern: `AgentConfig.for_type()`

**Goal:**
Add 16 new specialized agent types across 6 categories:

### Coding Agents (4)
1. **test-generation** - Creates comprehensive test cases
2. **documentation** - Generates docs, docstrings, READMEs
3. **refactoring** - Identifies and fixes code smells
4. **debug** - Analyzes errors and suggests fixes

### Writing & Communication Agents (3)
5. **writing** - Technical guides, tutorials, blog posts
6. **communication** - PR descriptions, issues, emails
7. **tutorial** - Educational content, onboarding materials

### Visual & Design Agents (1)
8. **diagram** - Mermaid diagrams, architecture visualizations

### Testing & QA Agents (1)
9. **qa-manual** - Manual testing procedures, QA scenarios

### Research & Analysis Agents (3)
10. **research** - Web research, technology evaluation
11. **log-analysis** - Parse and analyze logs for patterns
12. **performance-analysis** - Performance metrics and bottlenecks

### Security & Dependencies Agents (2)
13. **security-audit** - Security-focused code review
14. **dependency-analysis** - Dependency health and vulnerabilities

### Project Management Agents (2)
15. **migration-planning** - Plan and execute migrations
16. **configuration** - Manage and validate configs

**Result:** 20 total agent types (4 existing + 16 new)

---

## Design Decisions

### 1. Extend, Don't Replace
- Keep existing agents (explore, plan, code-review, general)
- Follow existing patterns and conventions
- Maintain backward compatibility
- Use established architecture (base classes, registry, factory)

### 2. Design Patterns Used

| Pattern | Application |
|---------|-------------|
| **Singleton** | AgentTypeRegistry (already exists) |
| **Factory** | AgentConfig.for_type() (already exists) |
| **Template Method** | Agent.execute() (defined in base) |
| **Strategy** | Each agent type = different strategy |
| **Command** | Agents encapsulate tasks |

### 3. Tool Access Strategy

Each agent type gets specific tool access aligned with its purpose:

| Agent Type | Allowed Tools | Rationale |
|------------|---------------|-----------|
| **test-generation** | glob, grep, read, write | Read code, write tests |
| **documentation** | glob, grep, read, write | Read code, write docs |
| **refactoring** | glob, grep, read, write, edit | Modify existing code |
| **debug** | glob, grep, read, bash | Read code, run diagnostics |
| **writing** | read, write, web-search, web-fetch | Research and compose |
| **communication** | read, write, git, github | Read context, draft messages |
| **tutorial** | glob, grep, read, write, web-search | Learn codebase, create guides |
| **diagram** | glob, grep, read, write | Analyze structure, create visuals |
| **qa-manual** | read, write, bash | Create procedures, test apps |
| **research** | web-search, web-fetch, read, write | Web research, synthesis |
| **log-analysis** | read, grep, bash, write | Parse logs, find patterns |
| **performance-analysis** | read, bash, grep, write | Analyze metrics, suggest fixes |
| **security-audit** | glob, grep, read, bash, write | Scan code, run security tools |
| **dependency-analysis** | read, bash, web-search, write | Check deps, find vulnerabilities |
| **migration-planning** | glob, grep, read, write, bash | Analyze code, plan migrations |
| **configuration** | glob, read, write, edit | Validate, manage configs |

### 4. Resource Limits

Each agent type has tailored resource limits:

| Agent Type | Max Tokens | Max Time | Rationale |
|------------|-----------|----------|-----------|
| test-generation | 40000 | 300s | Writing tests can be token-heavy |
| documentation | 35000 | 240s | Docs generation is moderate |
| refactoring | 45000 | 360s | Complex analysis and changes |
| debug | 30000 | 240s | Focused analysis |
| writing | 40000 | 300s | Long-form content |
| communication | 25000 | 180s | Concise messages |
| tutorial | 45000 | 360s | Comprehensive guides |
| diagram | 30000 | 240s | Visual generation |
| qa-manual | 35000 | 300s | Test procedure creation |
| research | 50000 | 400s | Deep research requires more tokens |
| log-analysis | 40000 | 300s | Large log files |
| performance-analysis | 35000 | 300s | Metrics analysis |
| security-audit | 45000 | 360s | Thorough security review |
| dependency-analysis | 35000 | 300s | Dependency tree analysis |
| migration-planning | 50000 | 400s | Complex planning |
| configuration | 30000 | 240s | Config validation |

---

## Architecture

### Component Structure

```
src/code_forge/agents/
├── base.py                      # [EXISTS] Agent, AgentConfig, AgentState
├── types.py                     # [MODIFY] Add 16 new AgentTypeDefinitions
├── result.py                    # [EXISTS] AgentResult
├── executor.py                  # [EXISTS] AgentExecutor
├── manager.py                   # [EXISTS] AgentManager
└── builtin/                     # [EXTEND] Add 16 new agent implementations
    ├── __init__.py              # [MODIFY] Export new agents
    ├── explore.py               # [EXISTS]
    ├── plan.py                  # [EXISTS]
    ├── review.py                # [EXISTS]
    ├── general.py               # [EXISTS]
    ├── test_generation.py       # [NEW] Coding
    ├── documentation.py         # [NEW] Coding
    ├── refactoring.py           # [NEW] Coding
    ├── debug.py                 # [NEW] Coding
    ├── writing.py               # [NEW] Writing & Communication
    ├── communication.py         # [NEW] Writing & Communication
    ├── tutorial.py              # [NEW] Writing & Communication
    ├── diagram.py               # [NEW] Visual & Design
    ├── qa_manual.py             # [NEW] Testing & QA
    ├── research.py              # [NEW] Research & Analysis
    ├── log_analysis.py          # [NEW] Research & Analysis
    ├── performance_analysis.py  # [NEW] Research & Analysis
    ├── security_audit.py        # [NEW] Security & Dependencies
    ├── dependency_analysis.py   # [NEW] Security & Dependencies
    ├── migration_planning.py    # [NEW] Project Management
    └── configuration.py         # [NEW] Project Management
```

---

## Implementation Steps

### Step 1: Define Agent Type Specifications
**File:** `agents/types.py`
**Action:** Add 16 new `AgentTypeDefinition` constants and register them

This is the core step - all agent types defined here with their prompts, tools, and limits.

---

### Step 2: Implement Coding Agents (4)

#### 2.1 Test Generation Agent
**File:** `agents/builtin/test_generation.py`
**Responsibilities:**
- Read source code to understand functionality
- Identify edge cases and boundary conditions
- Generate unit tests following project patterns
- Create integration tests where appropriate
- Use pytest (detected in project)

**Prompt Focus:**
- Happy path scenarios
- Edge cases and boundary conditions
- Error handling
- Null/empty inputs
- Integration points

#### 2.2 Documentation Agent
**File:** `agents/builtin/documentation.py`
**Responsibilities:**
- Extract and analyze code structure
- Generate docstrings (Google/NumPy/Sphinx style)
- Create README files
- Generate API documentation
- Update existing docs

**Prompt Focus:**
- Clear, concise descriptions
- Parameter and return documentation
- Examples where helpful
- Following existing style patterns

#### 2.3 Refactoring Agent
**File:** `agents/builtin/refactoring.py`
**Responsibilities:**
- Identify code smells
- Detect SOLID violations
- Suggest and implement refactorings
- Preserve behavior (tests must pass)
- Optimize performance bottlenecks

**Code Smells to Detect:**
- Duplicate code
- Long methods/classes
- Large parameter lists
- Feature envy
- Data clumps
- Primitive obsession

#### 2.4 Debug Agent
**File:** `agents/builtin/debug.py`
**Responsibilities:**
- Analyze error messages and stack traces
- Identify root causes
- Run diagnostic commands
- Suggest fixes with explanations
- Create reproduction steps

**Bug Patterns:**
- Off-by-one errors
- Null/None dereferences
- Race conditions
- Resource leaks
- Type mismatches
- Logic errors

---

### Step 3: Implement Writing & Communication Agents (3)

#### 3.1 Writing Agent
**File:** `agents/builtin/writing.py`
**Responsibilities:**
- Technical guides and tutorials
- Blog posts and articles
- Reports and summaries
- Long-form content with research

**Prompt Focus:**
- Clear, professional writing
- Proper structure (intro, body, conclusion)
- Technical accuracy
- Target audience awareness

#### 3.2 Communication Agent
**File:** `agents/builtin/communication.py`
**Responsibilities:**
- Draft PR descriptions
- Write issue comments
- Create release announcements
- Compose professional emails

**Prompt Focus:**
- Professional, appropriate tone
- Contextually aware
- Concise and clear
- Proper formatting

#### 3.3 Tutorial Agent
**File:** `agents/builtin/tutorial.py`
**Responsibilities:**
- Create step-by-step tutorials
- Generate onboarding documentation
- Explain complex concepts with examples
- Create troubleshooting guides

**Prompt Focus:**
- Step-by-step clarity
- Examples and code snippets
- Assumes beginner knowledge
- Progressive complexity

---

### Step 4: Implement Visual & Design Agents (1)

#### 4.1 Diagram Agent
**File:** `agents/builtin/diagram.py`
**Responsibilities:**
- Generate Mermaid diagrams
- Architecture visualizations
- Flowcharts and sequence diagrams
- ERDs and class diagrams

**Diagram Types:**
- Flowcharts
- Sequence diagrams
- Class diagrams
- Architecture diagrams
- State machines
- Entity-relationship diagrams

---

### Step 5: Implement Testing & QA Agents (1)

#### 5.1 QA Manual Agent
**File:** `agents/builtin/qa_manual.py`
**Responsibilities:**
- Create manual testing procedures
- Write user acceptance test scenarios
- Generate exploratory testing guides
- Design test case matrices

**Prompt Focus:**
- User-focused scenarios
- Given/When/Then format
- Edge case identification
- Clear pass/fail criteria

---

### Step 6: Implement Research & Analysis Agents (3)

#### 6.1 Research Agent
**File:** `agents/builtin/research.py`
**Responsibilities:**
- Deep web research
- Technology evaluation
- Competitive analysis
- Synthesize findings into reports

**Research Areas:**
- Library/framework comparisons
- Best practices
- Security implications
- Performance characteristics
- Industry trends

#### 6.2 Log Analysis Agent
**File:** `agents/builtin/log_analysis.py`
**Responsibilities:**
- Parse and analyze logs
- Find recurring errors
- Identify patterns and anomalies
- Extract root causes
- Generate analysis reports

**Analysis Types:**
- Error frequency analysis
- Pattern detection
- Anomaly detection
- Performance issues from logs
- Security incident detection

#### 6.3 Performance Analysis Agent
**File:** `agents/builtin/performance_analysis.py`
**Responsibilities:**
- Analyze profiling output
- Identify bottlenecks
- Review database query performance
- Suggest optimizations
- Memory usage analysis

**Analysis Focus:**
- CPU bottlenecks
- Memory leaks
- Database query optimization
- Network latency
- Algorithm complexity

---

### Step 7: Implement Security & Dependencies Agents (2)

#### 7.1 Security Audit Agent
**File:** `agents/builtin/security_audit.py`
**Responsibilities:**
- Security-focused code review
- OWASP Top 10 scanning
- Vulnerability detection
- Security best practices enforcement
- Dependency vulnerability scanning

**Security Checks:**
- SQL injection risks
- XSS vulnerabilities
- CSRF protection
- Authentication/authorization issues
- Sensitive data exposure
- Insecure deserialization
- Known CVEs in dependencies

#### 7.2 Dependency Analysis Agent
**File:** `agents/builtin/dependency_analysis.py`
**Responsibilities:**
- Analyze project dependencies
- Find outdated packages
- Identify security vulnerabilities
- Detect unused dependencies
- Map dependency tree

**Analysis Types:**
- Version currency
- Security vulnerabilities (CVEs)
- License compatibility
- Dependency conflicts
- Unused dependencies

---

### Step 8: Implement Project Management Agents (2)

#### 8.1 Migration Planning Agent
**File:** `agents/builtin/migration_planning.py`
**Responsibilities:**
- Plan code migrations
- Python version upgrades
- Framework migrations
- Sync to async conversions
- Risk assessment

**Migration Types:**
- Language version upgrades
- Framework migrations
- Library replacements
- Architecture changes
- Database migrations

#### 8.2 Configuration Agent
**File:** `agents/builtin/configuration.py`
**Responsibilities:**
- Validate configuration files
- Compare configs across environments
- Generate config templates
- Migrate config formats
- Document config options

**Config Operations:**
- Syntax validation
- Schema validation
- Environment comparison
- Format migration (YAML, TOML, JSON, ENV)
- Documentation generation

---

### Step 9: Update Module Exports
**File:** `agents/builtin/__init__.py`
**Action:** Export all 20 agent classes (4 existing + 16 new)

```python
from .code_review import CodeReviewAgent
from .communication import CommunicationAgent
from .configuration import ConfigurationAgent
from .debug import DebugAgent
from .dependency_analysis import DependencyAnalysisAgent
from .diagram import DiagramAgent
from .documentation import DocumentationAgent
from .explore import ExploreAgent
from .general import GeneralAgent
from .log_analysis import LogAnalysisAgent
from .migration_planning import MigrationPlanningAgent
from .performance_analysis import PerformanceAnalysisAgent
from .plan import PlanAgent
from .qa_manual import QAManualAgent
from .refactoring import RefactoringAgent
from .research import ResearchAgent
from .security_audit import SecurityAuditAgent
from .test_generation import TestGenerationAgent
from .tutorial import TutorialAgent
from .writing import WritingAgent

__all__ = [
    "CodeReviewAgent",
    "CommunicationAgent",
    "ConfigurationAgent",
    "DebugAgent",
    "DependencyAnalysisAgent",
    "DiagramAgent",
    "DocumentationAgent",
    "ExploreAgent",
    "GeneralAgent",
    "LogAnalysisAgent",
    "MigrationPlanningAgent",
    "PerformanceAnalysisAgent",
    "PlanAgent",
    "QAManualAgent",
    "RefactoringAgent",
    "ResearchAgent",
    "SecurityAuditAgent",
    "TestGenerationAgent",
    "TutorialAgent",
    "WritingAgent",
]
```

---

### Step 10: Comprehensive Testing

Create test files for all 16 new agents:

**Unit Tests:**
- `tests/unit/agents/test_types.py` - Verify all 16 types registered
- `tests/unit/agents/builtin/test_test_generation.py`
- `tests/unit/agents/builtin/test_documentation.py`
- `tests/unit/agents/builtin/test_refactoring.py`
- `tests/unit/agents/builtin/test_debug.py`
- `tests/unit/agents/builtin/test_writing.py`
- `tests/unit/agents/builtin/test_communication.py`
- `tests/unit/agents/builtin/test_tutorial.py`
- `tests/unit/agents/builtin/test_diagram.py`
- `tests/unit/agents/builtin/test_qa_manual.py`
- `tests/unit/agents/builtin/test_research.py`
- `tests/unit/agents/builtin/test_log_analysis.py`
- `tests/unit/agents/builtin/test_performance_analysis.py`
- `tests/unit/agents/builtin/test_security_audit.py`
- `tests/unit/agents/builtin/test_dependency_analysis.py`
- `tests/unit/agents/builtin/test_migration_planning.py`
- `tests/unit/agents/builtin/test_configuration.py`

**Integration Tests:**
- `tests/integration/test_all_specialized_agents.py` - End-to-end for all types

---

## Prompt Engineering Summary

Each agent needs a specialized system prompt. Key structure:

```
You are a [AGENT_TYPE] agent specialized in [DOMAIN].

Your task is to [PRIMARY_GOAL].

Guidelines:
1. [GUIDELINE_1]
2. [GUIDELINE_2]
...

Return structured results with:
- [OUTPUT_COMPONENT_1]
- [OUTPUT_COMPONENT_2]
...
```

**Prompt Quality Factors:**
- Clear role definition
- Specific task description
- Actionable guidelines (numbered list)
- Expected output structure
- Domain-specific best practices
- Examples where helpful

---

## Testing Strategy

### Unit Tests (Per Agent)
- Agent type definition validates
- Agent initialization
- agent_type property
- Tool access restrictions
- Resource limits

### Integration Tests
- End-to-end execution
- Tool calls work correctly
- Results have proper structure
- Permission system integration
- Hook system integration

### System Tests
- Spawn from REPL
- Concurrent execution
- Session integration
- Error handling

---

## Risks and Mitigations

### Risk 1: Scope Creep
**Problem:** 16 agents is a large implementation
**Mitigation:**
- Follow existing patterns closely
- Template-based implementation
- Incremental testing
- Category-by-category rollout

### Risk 2: Prompt Quality Variance
**Problem:** Some prompts may not be effective initially
**Mitigation:**
- Iterate based on testing
- Include clear examples in prompts
- Monitor real-world usage
- Gather feedback for improvements

### Risk 3: Tool Access Errors
**Problem:** Wrong tools = ineffective agents
**Mitigation:**
- Careful analysis per agent type
- Allow configuration overrides
- Monitor agent behavior
- Adjust based on testing

### Risk 4: Resource Limit Tuning
**Problem:** Hard to predict optimal limits
**Mitigation:**
- Conservative initial limits
- Monitor usage patterns
- Make limits configurable
- Log warnings approaching limits

### Risk 5: Integration Issues
**Problem:** 16 new agents = more integration points
**Mitigation:**
- Comprehensive integration tests
- Test with existing system
- No breaking changes
- Backward compatibility maintained

---

## Success Criteria

### Implementation Complete When:
1. 16 new AgentTypeDefinition constants in types.py
2. 16 new agent implementation files in builtin/
3. All agents registered in _register_builtins()
4. All agents exported from builtin/__init__.py
5. Registry lists 20 total types
6. All follow existing patterns

### Tests Pass When:
1. Unit tests for all 16 agent types pass
2. Integration tests verify execution
3. All existing tests still pass
4. Test coverage remains >90%
5. No regressions detected

### Documentation Complete When:
1. All planning documents created
2. All agents have clear prompts
3. Code has comprehensive docstrings
4. CHANGELOG updated

---

## Implementation Order

Suggested order to minimize risk:

### Phase 1: Coding Agents (Most Similar to Existing)
1. test-generation
2. documentation
3. refactoring
4. debug

### Phase 2: Research & Analysis (New Domain, Core Tools)
5. research
6. log-analysis
7. performance-analysis

### Phase 3: Security & Dependencies (Specialized)
8. security-audit
9. dependency-analysis

### Phase 4: Writing & Communication (Different Output Type)
10. writing
11. communication
12. tutorial

### Phase 5: Specialized Tools (Unique Requirements)
13. diagram
14. qa-manual
15. migration-planning
16. configuration

---

## Future Enhancements

After this phase:

1. **Agent Workflows** (FEAT-003)
   - Chain multiple agents
   - Conditional execution
   - Parallel execution

2. **Agent Analytics**
   - Usage statistics
   - Success rates
   - Performance metrics
   - Cost tracking

3. **Custom Agent Types**
   - User-defined agents
   - Plugin-based registration
   - Domain-specific agents

4. **Agent Collaboration**
   - Agents spawn sub-agents
   - Shared context
   - Hierarchical structures

5. **Agent Learning**
   - Feedback mechanisms
   - Prompt improvement
   - Result quality tracking

---

## References

- Current implementation: `src/code_forge/agents/`
- Existing patterns: `tests/unit/agents/`, `tests/integration/`
- Design patterns: Gang of Four, SOLID principles
- BDD specs: `GHERKIN.md`
- Testing strategy: `TESTS.md`
