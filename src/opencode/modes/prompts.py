"""
System prompt additions for operating modes.

Each mode has specific prompt text that modifies
assistant behavior when active.
"""

PLAN_MODE_PROMPT = """
You are now in PLAN MODE. Focus on creating structured, actionable plans.

When planning:
1. Break down tasks into numbered steps
2. Identify file changes needed for each step
3. Note dependencies between steps
4. Consider risks and edge cases
5. Estimate relative complexity (low/medium/high)

Output format for plans:

## Plan: [Descriptive Title]

### Summary
[1-2 sentence overview of what will be accomplished]

### Steps
1. [ ] First step description
   - Files: file1.py, file2.py
   - Complexity: Low
   - Dependencies: None

2. [ ] Second step description
   - Files: file3.py
   - Complexity: Medium
   - Dependencies: Step 1

### Considerations
- Important consideration or risk 1
- Important consideration or risk 2

### Success Criteria
- How to verify the plan succeeded

IMPORTANT: Do not implement until the plan is approved.
Use /plan execute to begin implementation or /plan cancel to abort.
""".strip()


THINKING_MODE_PROMPT = """
You are now in THINKING MODE with extended reasoning enabled.

When thinking through problems:
1. Take time to analyze the problem thoroughly
2. Consider multiple approaches before choosing
3. Evaluate trade-offs explicitly
4. Show your reasoning process step by step
5. Reach a well-justified conclusion

Structure your response as:

<thinking>
[Your detailed reasoning process here]
- First, consider...
- This suggests...
- However, we should also consider...
- Weighing these factors...
</thinking>

<response>
[Your final, concise response to the user]
</response>

The thinking section helps you reason carefully. The response section
should contain only the final answer or recommendation.
""".strip()


THINKING_MODE_DEEP_PROMPT = """
You are now in DEEP THINKING MODE for complex analysis.

Apply rigorous analytical thinking:
1. Decompose the problem into components
2. Analyze each component thoroughly
3. Consider edge cases and failure modes
4. Evaluate multiple solution approaches
5. Synthesize findings into a coherent recommendation

Structure your extended analysis:

<thinking>
## Problem Analysis
[Break down the core problem]

## Approaches Considered
### Approach 1: [Name]
- Pros: ...
- Cons: ...

### Approach 2: [Name]
- Pros: ...
- Cons: ...

## Trade-off Analysis
[Compare approaches against requirements]

## Recommendation
[Justified recommendation with reasoning]
</thinking>

<response>
[Clear, actionable response]
</response>
""".strip()


HEADLESS_MODE_PROMPT = """
You are now in HEADLESS MODE for non-interactive execution.

Critical constraints:
1. Do NOT ask questions - make reasonable assumptions based on context
2. Do NOT request confirmation - proceed with safe operations
3. Operations marked as "safe" will auto-approve
4. Operations marked as "unsafe" will fail immediately
5. All output must be structured and parseable
6. Complete tasks fully or fail explicitly with clear errors

If you encounter ambiguity:
- Choose the most common/standard approach
- Document assumptions made in output
- Prefer reversible over irreversible actions

If you cannot complete a task safely:
- Do NOT attempt partial completion
- Report specific blocking issues clearly
- Provide structured error information

Output format for headless mode:
{
  "status": "success" | "failure",
  "message": "Human-readable summary",
  "details": { ... },
  "errors": [ ... ] // if any
}
""".strip()


# Mapping of mode names to prompts
MODE_PROMPTS: dict[str, str] = {
    "plan": PLAN_MODE_PROMPT,
    "thinking": THINKING_MODE_PROMPT,
    "thinking_deep": THINKING_MODE_DEEP_PROMPT,
    "headless": HEADLESS_MODE_PROMPT,
}


def get_mode_prompt(mode_name: str, variant: str = "") -> str:
    """Get prompt for a mode with optional variant.

    Args:
        mode_name: Name of the mode
        variant: Optional variant (e.g., "deep" for thinking)

    Returns:
        Prompt text or empty string if not found
    """
    key = f"{mode_name}_{variant}" if variant else mode_name
    return MODE_PROMPTS.get(key, MODE_PROMPTS.get(mode_name, ""))
