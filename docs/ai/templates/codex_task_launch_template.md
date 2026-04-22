# Codex Task Launch Template

Repository root:
C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie

Use this template as the starting frame for major Codex tasks in this repo.

## Core Instructions

- Use the repo as source of truth.
- Preserve working architecture.
- Do not rebuild frameworks from scratch.
- Respect Windows write-size limitations.
- Write large files in small batches.
- Validate every required output.
- Log created and validated files.
- Do not claim completion if required outputs are missing.

## Required Guardrail Block

### Windows Write Constraint

This repo runs in Windows shells where command and patch payload sizes are limited.

You must assume:
- safe write size per operation is approximately 2 KB to 4 KB
- files larger than approximately 3 KB must be written in small batches
- large tables should prefer CSV plus Markdown summary

Write method:
1. create file
2. write first section
3. append remaining sections in small batches
4. validate file exists and is non-empty
5. log created files and validation results

Recovery:
- do not restart the whole task after a large write failure
- keep completed artifacts
- continue with smaller writes
- finish only missing outputs
- run final validation

## Task Framing Checklist

Before starting:
- confirm repo root
- identify target files
- identify existing artifacts to preserve
- identify required outputs
- identify large-output risk

Before finishing:
- confirm all required outputs exist
- confirm outputs are non-empty
- confirm outputs are readable
- confirm logs are written
- return final handoff in the requested structure
