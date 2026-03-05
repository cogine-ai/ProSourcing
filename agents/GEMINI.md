# Gemini Skills

This extension provides two skills for enhanced productivity:

## Skills

### Nano Banana Pro (Image Generation)

Generate images using Google's Gemini 2.5 Flash model. Triggered by requests like "generate an image", "create an image", or "nano banana".

**Prerequisites:**
- [uv](https://docs.astral.sh/uv/) - Python package manager
- `GEMINI_API_KEY` environment variable

**Usage:**
```bash
uv run "${SKILL_DIR}/scripts/image.py" \
  --prompt "Your image description" \
  --output "/path/to/output.png" \
  --aspect landscape  # optional: square, landscape, portrait
  --reference "/path/to/reference.png"  # optional
```

**Prompt tips:** Be specific about subject, style, colors, mood, and context.

### Frontend Design

Create distinctive, production-grade frontend interfaces. Triggered by requests to build web components, pages, landing pages, or dashboards.

Emphasizes bold aesthetic choices, avoiding generic AI aesthetics. Focus on:
- Distinctive typography (avoid Inter, Roboto, Arial)
- Cohesive color themes with sharp accents
- Purposeful animations and micro-interactions
- Unexpected layouts and spatial composition
