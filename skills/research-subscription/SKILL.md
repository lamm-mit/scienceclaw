# Research Subscription Skill Summary

This skill handles **scheduled and recurring tasks** like literature digests, delayed reports, and reminders.

## Key Usage

Activate when users request:
- Scheduled literature updates or paper tracking
- Delayed reports (e.g., tomorrow morning)
- Recurring push notifications
- Time-based reminders

## Core Action

Call `scientify_cron_job` with:
- **`action`**: "upsert" (create/update), "list", or "remove"
- **`topic`**: for research subscriptions (e.g., "LLM alignment")
- **`message`**: for plain reminders only

## Scheduling Syntax

Use formats like:
- `daily 08:00 Asia/Shanghai`
- `weekly mon 09:30 Asia/Shanghai`
- `every 6h`
- `at 2m`

## Delivery Options

Optionally specify `channel` ("feishu", "telegram", "slack", etc.) and `to` (recipient ID). Default routing applies if unset.

## Research Quality Standards

For recurring research jobs:
- Aim for ≥80% full-text coverage of core papers
- Maintain ≥90% evidence-binding rate
- Keep citation errors <2%

## Response Format

Confirm: job status, effective schedule with timezone, delivery target, and next action options.

---
🐍Scientify
