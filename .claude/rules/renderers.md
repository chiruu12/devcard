---
paths:
  - "src/devcard/renderers/**/*.py"
---

# Renderer Conventions

## Pattern-Matching
Before writing a new renderer, read `src/devcard/renderers/terminal.py` for the input pattern.

## Rules
- Every renderer function takes a `DevCard` model and returns a string (or bytes for PNG)
- Renderers are pure functions — no I/O, no API calls, no side effects. File writing happens in the CLI layer.
- Accept a `Theme` dataclass for visual renderers (SVG, HTML, PNG). Terminal renderer uses Rich styles directly.

## SVG-Specific Rules (CRITICAL for GitHub embedding)
- NO `foreignObject` elements — GitHub strips them
- NO `<script>` tags — GitHub strips them
- NO external resources (images, fonts, stylesheets) — GitHub blocks them
- Use system font stack: `"Segoe UI", Ubuntu, "Helvetica Neue", sans-serif`
- Use monospace stack: `"SF Mono", "Cascadia Code", "Fira Code", Consolas, monospace`
- CSS animations inside `<style>` are OK
- Build SVG as string concatenation or template — no SVG library dependency
- Target output size under 30KB
- Dynamic height based on content — calculate section heights, sum for viewBox
- Language colors: use GitHub Linguist color values (hardcoded dict for top 30 languages)
- Always include `xmlns="http://www.w3.org/2000/svg"` on root element

## Markdown Renderer
- Output must be valid GitHub Flavored Markdown
- Use tables for structured data, not code blocks
- No HTML tags — pure markdown only
