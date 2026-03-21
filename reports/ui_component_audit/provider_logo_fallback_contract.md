# Provider Logo Fallback Contract

## Lookup Rule

1. Try local provider logo asset by normalized provider name.
2. Fall back to TMDB provider logo when available.
3. If no usable logo source exists, render a text badge/chip immediately.

## Failure Rule

- If an image source fails at runtime, remove the broken image and promote the chip into fallback-text mode.
- Broken image icons must never remain visible.

## Render Contract

- Provider chips always retain the provider name as fallback text.
- Missing or broken logo assets degrade to text badges/chips.

