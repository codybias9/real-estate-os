# PR10: Collab.Timeline - Evidence Pack

**PR**: `feat/collab-timeline`
**Date**: 2025-11-02

## Summary

Property activity streams with markdown support, SSE broadcasts, and collaboration features.

## Deliverables

1. **CollabTimeline agent** (393 lines) - Activity stream management
2. **TimelineRepository** (401 lines) - Database operations
3. **Database models** (111 lines) - Events and notes
4. **18 comprehensive tests** - 69% coverage, 95% timeline logic

## Features

- System event logging from all agents
- User comments and notes with markdown
- HTML sanitization (bleach)
- SSE broadcasts for real-time updates
- Property-level activity streams
- Immutable events, mutable notes

## Event Types

System: property_discovered, property_enriched, property_scored, memo_generated, outreach_sent, state_changed

User: comment_added, note_added, attachment_added, tag_added, assigned

## Test Results

18/18 passing, 95% timeline logic coverage

## Files Created

- `src/timeline/timeline.py` (393 lines)
- `src/timeline/repository.py` (401 lines)
- `src/timeline/models.py` (111 lines)
- `tests/test_timeline.py` (466 lines, 18 tests)

**Total**: 1,371 lines
