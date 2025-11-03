workspace "ITEP Agentic AI Platform" "Agent Fleet Architecture with Router Agent as orchestrator" {

    model {
        # People
        ciscoIT = person "Cisco IT Personnel" "Developers, DevOps engineers, product managers" "User"

        # External Systems
        circuit = softwareSystem "Circuit" "ChatGPT-like UI for task submission (future A2A support)" "External"
        ides = softwareSystem "IDEs" "IDE extensions for in-editor assistance" "External"
        bots = softwareSystem "Chat Bots" "Slack/WebEx bots for conversational access" "External"

        github = softwareSystem "GitHub" "Code repository and version control" "External"
        jira = softwareSystem "JIRA" "Issue tracking and project management" "External"
        jenkins = softwareSystem "Jenkins" "CI/CD orchestration and build automation" "External"
        sonarqube = softwareSystem "SonarQube" "Code quality and security scanning" "External"
        splunk = softwareSystem "Splunk" "Logging and monitoring" "External"
        other = softwareSystem "Other" "Other external systems" "External"

        # ITEP Platform
        itep = softwareSystem "ITEP Agentic AI Platform" "Intelligent orchestration platform for AI agents using A2A protocol" {

            # Router Agent with internal components
            routerAgent = container "Router Agent" "Orchestrates multi-agent execution, breaks down tasks, aggregates results" "LangGraph Agent" {
                guardrails = component "Guardrails" "Validates requests are on-topic using built-in LLM" "Component"
                taskBreakdown = component "Task Breakdown" "Analyzes complexity and breaks requests into sub-tasks based on agent capabilities" "Component"
                orchestrator = component "Orchestrator" "Dispatches tasks to agents, monitors execution, handles parallel execution" "Component"
                summarizer = component "Summarizer" "Aggregates results from all agents (only task Router executes)" "Component"
                registry = component "Agent Registry" "Discovers agents via LangGraph API, caches agent cards and capabilities" "Component"

                # Internal Router flow
                guardrails -> taskBreakdown "Routes valid requests to"
                taskBreakdown -> registry "Reads agent capabilities from"
                taskBreakdown -> orchestrator "Sends plan to"
                orchestrator -> registry "Queries agent details from"
                orchestrator -> summarizer "Sends results to"
            }

            # Other Agents
            codaAgent = container "Coda Agent" "Remediates SonarQube violations (accesses SonarQube, Git, Jenkins, JIRA)" "LangGraph Agent"
            askCodyAgent = container "AskCody Agent" "Diagnoses CI/CD issues (accesses Git, Jenkins, build logs)" "LangGraph Agent"
            otherAgents = container "Other Agents" "Additional specialized agents discovered dynamically" "LangGraph Agents"

            # Platform Services
            langGraphAPI = container "LangGraph API" "Provides /assistants/search, /a2a endpoints for agent discovery and communication" "REST API" "Database"
            authService = container "Auth Service" "Validates tokens, manages authorization" "Service"
            monitoring = container "Monitoring" "Platform observability and logging" "Service"

            # Container relationships
            routerAgent -> langGraphAPI "Discovers agents" "GET /assistants/search"
            routerAgent -> langGraphAPI "Fetches agent cards" "GET /a2a/{id}/card"
            routerAgent -> codaAgent "Delegates SonarQube tasks" "POST /a2a/{id} (JSON-RPC)"
            routerAgent -> askCodyAgent "Delegates CI/CD tasks" "POST /a2a/{id} (JSON-RPC)"
            routerAgent -> otherAgents "Delegates tasks" "POST /a2a/{id} (JSON-RPC)"

            monitoring -> routerAgent "Collects metrics"
            monitoring -> codaAgent "Collects metrics"
            monitoring -> askCodyAgent "Collects metrics"

            # Component level relationships
            registry -> langGraphAPI "Discovers agents" "GET /assistants/search"
            registry -> codaAgent "Fetches agent cards" "GET /a2a/{id}/card"
            registry -> askCodyAgent "Fetches agent cards" "GET /a2a/{id}/card"
            registry -> otherAgents "Fetches agent cards" "GET /a2a/{id}/card"

            orchestrator -> codaAgent "Dispatches tasks" "POST /a2a/{id} (JSON-RPC)"
            orchestrator -> askCodyAgent "Dispatches tasks" "POST /a2a/{id} (JSON-RPC)"
            orchestrator -> otherAgents "Dispatches tasks" "POST /a2a/{id} (JSON-RPC)"
        }

        # User -> Client relationships
        ciscoIT -> circuit "Submits tasks via" "HTTPS"
        ciscoIT -> ides "Uses"
        ciscoIT -> bots "Chats with" "WebEx/Slack"

        # Client -> ITEP relationships
        circuit -> itep "Sends requests to" "A2A Protocol (future)"
        circuit -> authService "Authenticates" "HTTPS"
        circuit -> routerAgent "Submits tasks" "A2A Protocol (future)"
        ides -> itep "Invokes agents via" "A2A/MCP"
        bots -> itep "Delegates tasks to" "A2A Protocol"

        # ITEP -> External Systems relationships
        itep -> github "Accesses code" "Git/REST API"
        itep -> jira "Manages tickets" "REST API"
        itep -> jenkins "Triggers builds, fetches logs" "REST API"
        itep -> sonarqube "Queries violations" "REST API"
        itep -> splunk "Logs, traces" "REST API"
        itep -> other "TBC" "TBC"

        # Agent -> External Systems relationships
        codaAgent -> sonarqube "Queries violations" "REST API"
        codaAgent -> github "Creates PRs, commits fixes" "Git/REST"
        codaAgent -> jenkins "Triggers builds" "REST API"

        askCodyAgent -> jenkins "Fetches build logs" "REST API"
        askCodyAgent -> github "Analyzes commits" "Git/REST"

        # Component level - User interactions
        ciscoIT -> guardrails "Submits request" "HTTP/A2A"
        ciscoIT -> orchestrator "Receives status updates" "Streaming"
        summarizer -> ciscoIT "Returns final response" "HTTP/A2A"
    }

    views {
        # System Context view
        systemContext itep "SystemContext" {
            include *
            autoLayout lr

            description "System Context diagram showing ITEP platform in the broader Cisco IT ecosystem"

            properties {
                "structurizr.groups" "false"
            }
        }

        # Container view
        container itep "Container" {
            include *
            autoLayout lr

            description "Container diagram showing the internal containers of ITEP platform"
        }

        # Component view - Router Agent
        component routerAgent "Component" {
            include *
            include codaAgent
            include askCodyAgent
            include otherAgents
            include langGraphAPI
            autoLayout lr

            description "Component diagram showing the internal architecture of the Router Agent"
        }

        # Optional: Filtered views for clarity

        # System Context - simplified (without all external systems)
        systemContext itep "SystemContextSimplified" {
            include ciscoIT
            include circuit ides bots
            include itep
            include github jira jenkins sonarqube
            autoLayout lr

            description "Simplified System Context showing key external systems"
        }

        styles {
            element "Software System" {
                background #1168bd
                color #ffffff
                shape RoundedBox
            }
            element "External" {
                background #999999
                color #ffffff
            }
            element "Container" {
                background #438dd5
                color #ffffff
                shape RoundedBox
            }
            element "Component" {
                background #85bbf0
                color #000000
                shape Component
            }
            element "Person" {
                background #08427b
                color #ffffff
                shape Person
            }
            element "Database" {
                shape Cylinder
            }
            element "User" {
                background #08427b
                color #ffffff
            }
        }

        themes default
    }

    configuration {
        scope softwaresystem
    }
}
