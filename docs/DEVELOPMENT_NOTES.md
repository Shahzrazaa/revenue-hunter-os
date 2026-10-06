# Development Notes

## Problem framing

The project started from a recurring problem in freelance / independent work: many possible opportunities, limited time, and no useful connection between "research activity" and actual revenue.

The product rule became simple:

> A lead is not revenue. A pitch is not revenue. Only money marked Paid counts as collected revenue.

## Why heuristic scoring first

A transparent score is easier to inspect and change than an opaque model. The current version therefore uses explicit business rules. A future ML/LLM layer should be evaluated against conversion outcomes rather than added simply because AI is available.

## Production improvements

- Replace JSON storage with PostgreSQL/SQLite.
- Add authentication and per-user data separation.
- Validate external URLs and email inputs more strictly.
- Use a background queue for sending and enrichment.
- Add encrypted secret management.
- Add CSRF protection and rate limiting for deployed use.
- Keep human approval before any outbound message.
