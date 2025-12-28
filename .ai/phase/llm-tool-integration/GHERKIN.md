# FEAT-002: Multi-Agent Tools & Web Search Integration - BDD Scenarios

**Phase:** llm-tool-integration
**Version Target:** 1.10.0

---

## Feature: TaskTool Agent Spawning

### Scenario 1: Spawn an explore agent

```gherkin
Given the TaskTool is registered in the tool registry
And the "explore" agent type exists
When the LLM calls TaskTool with agent_type="explore" and task="Find all Python files"
Then an explore agent is spawned
And the agent executes the task
And the result is returned to the LLM
```

### Scenario 2: Spawn a code-review agent

```gherkin
Given the TaskTool is registered in the tool registry
And the "code-review" agent type exists
When the LLM calls TaskTool with agent_type="code-review" and task="Review the auth module"
Then a code-review agent is spawned
And the agent analyzes the specified code
And the review results are returned
```

### Scenario 3: Unknown agent type error

```gherkin
Given the TaskTool is registered in the tool registry
When the LLM calls TaskTool with agent_type="nonexistent" and task="Do something"
Then an error is returned
And the error message indicates unknown agent type
And a list of valid agent types is provided
```

### Scenario 4: Task with RAG context

```gherkin
Given the TaskTool is registered
And RAG is enabled with indexed project
When the LLM calls TaskTool with use_rag=true
Then the spawned agent receives RAGManager
And the agent can query the RAG index
And relevant context is included in agent's work
```

### Scenario 5: Task without RAG context

```gherkin
Given the TaskTool is registered
And RAG is enabled with indexed project
When the LLM calls TaskTool with use_rag=false
Then the spawned agent does not receive RAGManager
And the agent works without RAG context
```

### Scenario 6: Background execution

```gherkin
Given the TaskTool is registered
When the LLM calls TaskTool with wait=false
Then the agent is spawned in background
And the tool returns immediately
And a task ID is returned for tracking
```

### Scenario 7: All agent types accessible

```gherkin
Given the TaskTool is registered
When I list all available agent types
Then all 20+ specialized agents are available
And each agent type can be spawned
```

---

## Feature: WebSearchBaseTool

### Scenario 8: Basic web search

```gherkin
Given the WebSearchBaseTool is registered in the tool registry
When the LLM calls WebSearchBaseTool with query="Python async patterns"
Then a web search is performed
And search results are returned
And results include titles, URLs, and snippets
```

### Scenario 9: Search with result limit

```gherkin
Given the WebSearchBaseTool is registered
When the LLM calls WebSearchBaseTool with query="pytest" and num_results=5
Then at most 5 results are returned
```

### Scenario 10: Search with domain filtering

```gherkin
Given the WebSearchBaseTool is registered
When the LLM calls WebSearchBaseTool with query="Python" and allowed_domains=["docs.python.org"]
Then only results from docs.python.org are returned
```

### Scenario 11: Search with blocked domains

```gherkin
Given the WebSearchBaseTool is registered
When the LLM calls WebSearchBaseTool with query="Python" and blocked_domains=["w3schools.com"]
Then no results from w3schools.com are returned
```

### Scenario 12: Search with specific provider

```gherkin
Given the WebSearchBaseTool is registered
And DuckDuckGo provider is available
When the LLM calls WebSearchBaseTool with provider="duckduckgo"
Then DuckDuckGo is used for the search
```

### Scenario 13: Search no results

```gherkin
Given the WebSearchBaseTool is registered
When the LLM calls WebSearchBaseTool with query="xyznonexistent123456"
Then an empty result set is returned
And no error is raised
And a message indicates no results found
```

---

## Feature: WebFetchBaseTool

### Scenario 14: Fetch URL as markdown

```gherkin
Given the WebFetchBaseTool is registered in the tool registry
When the LLM calls WebFetchBaseTool with url="https://example.com" and format="markdown"
Then the page is fetched
And content is converted to markdown
And the markdown content is returned
```

### Scenario 15: Fetch URL as plain text

```gherkin
Given the WebFetchBaseTool is registered
When the LLM calls WebFetchBaseTool with url="https://example.com" and format="text"
Then the page is fetched
And content is converted to plain text
And HTML tags are stripped
```

### Scenario 16: Fetch with caching

```gherkin
Given the WebFetchBaseTool is registered
And a URL was recently fetched
When the LLM calls WebFetchBaseTool with the same URL and use_cache=true
Then the cached content is returned
And no network request is made
```

### Scenario 17: Fetch without caching

```gherkin
Given the WebFetchBaseTool is registered
And a URL was recently fetched
When the LLM calls WebFetchBaseTool with the same URL and use_cache=false
Then a fresh network request is made
And the new content is returned
```

### Scenario 18: Fetch with timeout

```gherkin
Given the WebFetchBaseTool is registered
And a server is slow to respond
When the LLM calls WebFetchBaseTool with timeout=5
Then the request times out after 5 seconds
And an appropriate error is returned
```

### Scenario 19: Invalid URL handling

```gherkin
Given the WebFetchBaseTool is registered
When the LLM calls WebFetchBaseTool with url="not-a-valid-url"
Then an error is returned
And the error indicates invalid URL
```

### Scenario 20: HTTPS enforcement

```gherkin
Given the WebFetchBaseTool is registered
When the LLM calls WebFetchBaseTool with url="http://example.com"
Then the URL is upgraded to https://example.com
And the secure version is fetched
```

---

## Feature: Tool Registration

### Scenario 21: All tools registered at startup

```gherkin
Given Code-Forge starts up
When register_all_tools() is called
Then TaskTool is registered
And WebSearchBaseTool is registered
And WebFetchBaseTool is registered
And all tools are accessible
```

### Scenario 22: Tools visible in tool list

```gherkin
Given all tools are registered
When I list all available tools
Then "Task" appears in the list
And "WebSearch" appears in the list
And "WebFetch" appears in the list
```

### Scenario 23: No tool name conflicts

```gherkin
Given existing tools are registered
When new tools are registered
Then no name conflicts occur
And all tools have unique names
```

---

## Feature: LLM Tool Access

### Scenario 24: LLM can call TaskTool

```gherkin
Given the LLM has access to registered tools
When the LLM decides to spawn an agent
Then TaskTool parameters are provided
And the tool is invoked
And results are returned to LLM
```

### Scenario 25: LLM can call WebSearchBaseTool

```gherkin
Given the LLM has access to registered tools
When the LLM needs to search for information
Then WebSearchBaseTool parameters are provided
And the search is performed
And results inform LLM's response
```

### Scenario 26: LLM can call WebFetchBaseTool

```gherkin
Given the LLM has access to registered tools
When the LLM needs to read a web page
Then WebFetchBaseTool parameters are provided
And the page is fetched
And content informs LLM's response
```

---

## Feature: Error Handling

### Scenario 27: Agent spawn failure

```gherkin
Given the TaskTool is registered
And the agent manager has an error
When the LLM calls TaskTool
Then an appropriate error is returned
And the error is informative
And no crash occurs
```

### Scenario 28: Network failure in search

```gherkin
Given the WebSearchBaseTool is registered
And the network is unavailable
When the LLM calls WebSearchBaseTool
Then an appropriate error is returned
And the error indicates network issue
```

### Scenario 29: Network failure in fetch

```gherkin
Given the WebFetchBaseTool is registered
And the network is unavailable
When the LLM calls WebFetchBaseTool
Then an appropriate error is returned
And the error indicates network issue
```

### Scenario 30: Rate limiting

```gherkin
Given the WebSearchBaseTool is registered
And the search provider returns rate limit error
When the LLM calls WebSearchBaseTool
Then an appropriate error is returned
And the error indicates rate limiting
```
