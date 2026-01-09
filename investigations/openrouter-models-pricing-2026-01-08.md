# OpenRouter Models & Pricing Research

> Historical draft. Canonical pricing now lives in `docs/OPENROUTER_MODELS.md`.

**Research Date**: 2026-01-08
**Status**: 📋 Draft - Awaiting Gemini Research
**Researcher**: Gemini + Claude Validation
**Tags**: #openrouter #ai-models #pricing #cost-optimization

---

## Research Brief for Gemini

### Topic
OpenRouter AI Model Availability and Pricing (January 2025/2026)

### Context
Building a conversational AI experiment ("Am I Alive?") that needs to:
- Generate thoughts and social media posts
- Have good reasoning capabilities
- Work within a $5/month budget
- Currently using Gemini Flash but hitting quota limits

Need to find cost-effective alternatives via OpenRouter API.

### Key Questions

1. **What models are available on OpenRouter as of January 2025?**
   - Full list not needed, but overview of major providers

2. **Which models are the cheapest per 1M tokens?**
   - Focus on models under $1/1M tokens
   - Include both input and output pricing
   - Note any free tier models

3. **Which Claude models are available and their costs?**
   - Claude 3.5 Sonnet
   - Claude 3.5 Haiku
   - Claude 3 Opus (if available)
   - Any other Claude variants
   - Include exact model IDs for API calls

4. **Which Google Gemini models are available and their costs?**
   - Gemini 2.0 Flash
   - Gemini 1.5 Pro
   - Gemini 1.5 Flash
   - Any other Gemini variants
   - Include exact model IDs for API calls

5. **What other cheap but capable models exist?**
   - Under $1/1M tokens preferred
   - Under $0.50/1M tokens highly preferred
   - Must be capable of:
     - Coherent conversational text
     - Basic reasoning
     - Creative writing for social posts
   - Include providers like: Meta (Llama), Mistral, DeepSeek, Qwen, etc.

### Required Coverage

- **Model IDs**: Exact strings used in OpenRouter API calls (e.g., "anthropic/claude-3.5-sonnet")
- **Pricing**: Per 1M input tokens AND per 1M output tokens (separately)
- **Context Window**: How many tokens each model can handle
- **Rate Limits**: Any known rate limits on OpenRouter
- **Free Tier**: Any models with free tier or credits
- **Capabilities**: Brief note on each model's strengths

### Depth Level
Intermediate - Need practical details for implementation, not deep technical specs

### Output Format
Please provide:

1. **Executive Summary** (2-3 paragraphs)
   - Overview of OpenRouter pricing landscape
   - Best options for $5/month budget
   - Key tradeoffs to consider

2. **Detailed Model List** organized by provider:
   - **Claude Models**
   - **Google Gemini Models**
   - **Budget Models** (under $1/1M tokens)
   - **Ultra-Budget Models** (under $0.50/1M tokens)

For each model include:
```
Model Name
- API ID: "provider/model-name"
- Input: $X.XX / 1M tokens
- Output: $Y.YY / 1M tokens
- Context: XXk tokens
- Best for: [use case]
```

3. **Budget Calculation Examples**
   - How many tokens does $5/month buy with different models?
   - Example: "X thoughts per day" or "Y posts per day"

4. **Practical Recommendations**
   - Best model for conversational AI on tight budget
   - Cost vs quality tradeoffs
   - Mixing strategies (cheap model for thoughts, better model for posts)

5. **Resource Links**
   - OpenRouter official pricing page
   - OpenRouter API documentation
   - Any comparison tools or calculators

### Success Criteria
- Complete pricing data for all requested models
- Actual API model IDs (not just marketing names)
- Clear cost comparison for $5/month budget
- Actionable recommendation for this specific use case

---

## Instructions

**User: Please copy everything below the "Research Brief for Gemini" section above and send it to Gemini (Google AI Studio, Gemini API, or any Gemini interface).**

When you return with Gemini's response, I'll:
1. Validate the accuracy and completeness
2. Check for any gaps or inconsistencies
3. Request follow-up research if needed
4. Store the validated results in this file

---

## Gemini Research Results

[Awaiting results - paste Gemini's response here]

---

*This file will be updated with validated research results once received from Gemini.*
