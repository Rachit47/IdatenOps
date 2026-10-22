# Idaten Ops
### AI-Assisted Workflow for Pre-Owned Automotive Retail

**Investigate overdue leads. Recommend the next action. Keep humans in control.**

## Problem Statement

Pre-owned car dealerships manage buyer enquiries, follow-ups, vehicle availability, and test-drive appointments across multiple operational workflows. When lead history, inventory status, and follow-up activities are fragmented, sales teams can struggle to identify which leads need attention and determine the appropriate next step.

Idaten Ops explores how agentic AI can help sales teams investigate overdue leads, retrieve relevant sales procedures, and recommend evidence-backed actions while keeping business decisions under human control.

## What It Does

- **Lead Recovery:** Identify overdue leads using deterministic business rules.
- **AI-Powered Investigation:** Analyze lead history, buyer preferences, existing tasks, and relevant inventory.
- **Knowledge-Grounded Recommendations:** Use retrieval-augmented generation (RAG) to retrieve relevant sales procedures.
- **Human-in-the-Loop Approval:** Let operators review, approve, or reject proposed actions.
- **Safe Business Execution:** Revalidate business conditions before creating follow-up tasks or test-drive bookings.
- **Agent Observability:** Record execution traces, decisions, approvals, and action outcomes.

## Technology Stack

Python · FastAPI · Pydantic · LangGraph · MCP · MySQL · Chroma · React · TypeScript

## Architecture and Design

For the detailed problem definition, functional requirements, architecture, workflow diagrams, and database design, see the [Idaten Ops Software Design Document](docs/IdatenOps_Software_Design_Document.md).

## Project Scope

Idaten Ops is designed as a modular monolith with a human-approved agent workflow. The initial implementation does not send customer communications or integrate with live dealership systems.

---

*This project explores the application of agentic AI to dealership operations, with an emphasis on explainable recommendations, controlled execution, and backend reliability.*

