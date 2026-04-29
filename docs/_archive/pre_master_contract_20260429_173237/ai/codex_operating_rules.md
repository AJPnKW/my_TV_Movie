# Codex Operating Rules

Repository root:
C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie

## 1. Windows Write Constraint

This repo runs in Windows shells where command and patch payload size limits can break large writes.

Assume:
- single large writes are unsafe
- maximum safe write size per operation is approximately 2 KB to 4 KB
- large files must be written in smaller sections

Never attempt one large patch or write for:
- long Markdown reports
- long HTML mockups
- large CSV matrices
- large prompt artifacts

## 2. Required Write Strategy

For files larger than approximately 3 KB or 150 lines:

1. Create the file first.
2. Write the header or first section.
3. Append the remaining sections in small batches.
4. Validate:
   - exists
   - non-empty
   - readable
5. Log result.

For files larger than approximately 20 KB:
- mandatory staged writes
- mandatory validation
- prefer CSV plus Markdown summary instead of one giant Markdown table

## 3. Repo Preservation Rules

1. Use existing repo files as source of truth.
2. Never rebuild frameworks from scratch.
3. Preserve stable:
   - file paths
   - IDs
   - selectors
   - data-* hooks
   - event wiring
4. Analysis and mockup tasks must not refactor production pages.
5. Continue partial work instead of restarting from scratch.

## 4. Artifact Preferences

Preferred patterns:
- matrix -> CSV primary + Markdown summary
- long report -> sectioned Markdown
- mockup -> standalone HTML, sectioned write
- every task -> execution log and summary

## 5. Validation Rules

Every required output must be confirmed as:
- existing
- non-empty
- readable

If any required file is missing:
- task is not complete

## 6. Recovery Rule

If a write or patch fails due to command-size or payload-size limits:

1. Keep completed artifacts.
2. Do not redo broad analysis.
3. Split the remaining writes.
4. Finish only missing outputs.
5. Validate all required outputs.
6. Then return final handoff.

## 7. UI Standardization Specific Rules

For card and popup baseline work in this repo:
1. Discover and document current variants first.
2. Derive approved baseline targets.
3. Generate review mockups before production refactor.
4. Map element and function reuse before implementation.
5. Refactor helpers before broad page swaps.
6. Preserve page-specific exceptions where justified.
