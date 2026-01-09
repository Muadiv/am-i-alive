# OpenRouter Models & Pricing - Genesis Project

**Last Updated:** 2026-01-08
**Budget:** $5/month (resets monthly)
**Strategy:** Multi-tier rotation to maximize survival

---

## 🎯 Executive Summary

OpenRouter provides access to 200+ AI models with a single API key. For our $5/month budget, we have excellent options:

### Key Findings:
1. **FREE models available** - Several capable models at $0 cost
2. **Ultra-cheap models** - High quality at $0.02-0.10 per 1M tokens
3. **Claude Haiku** - Available at $0.25/1M (8x cheaper than Sonnet)
4. **Token capacity** - Can generate 20-250M tokens/month depending on model choice

### Budget Breakdown (Per Month):
- **Free models**: Unlimited tokens, variable quality
- **Llama 3.2 3B** ($0.02/1M): 250 million tokens = ~500k posts
- **Gemma 3 4B** ($0.017/1M): 290 million tokens
- **Claude 3 Haiku** ($0.25/1M): 20 million tokens = ~40k posts
- **Claude 3.5 Haiku** ($0.80/1M): 6.25 million tokens = ~12k posts
- **Claude Sonnet 4.5** ($3/1M): 1.66 million tokens = ~3k posts

---

## 📊 Model Tiers

### 🆓 FREE TIER (Unlimited Use)
Perfect for frequent, low-stakes operations.

| Model | API ID | Context | Intelligence | Best For |
|-------|--------|---------|--------------|----------|
| **Qwen3 Coder** | `qwen/qwen3-coder:free` | 262k | 6/10 | Code, technical thoughts |
| **Mistral Devstral** | `mistralai/devstral-2512:free` | 262k | 6/10 | General reasoning |
| **NVIDIA Nemotron** | `nvidia/nemotron-nano-9b-v2:free` | 128k | 5/10 | Quick responses |
| **Xiaomi MiMo V2** | `xiaomi/mimo-v2-flash:free` | 262k | 5/10 | Simple tasks |

**Strategy**: Use for daily thoughts, internal reasoning, low-stakes content.

---

### 💰 ULTRA-CHEAP TIER ($0.02-0.10 / 1M tokens)
Best bang-for-buck. Quality models at minimal cost.

| Model | API ID | Input | Output | Context | Int | Best For |
|-------|--------|-------|--------|---------|-----|----------|
| **Gemma 3 4B** | `google/gemma-3-4b-it` | $0.017 | $0.068 | 96k | 7/10 | Conversational |
| **Llama 3.2 3B** | `meta-llama/llama-3.2-3b-instruct` | $0.020 | $0.020 | 131k | 7/10 | Social posts |
| **Mistral Nemo** | `mistralai/mistral-nemo` | $0.020 | $0.040 | 131k | 7/10 | Balanced |
| **Llama 3.1 8B** | `meta-llama/llama-3.1-8b-instruct` | $0.020 | $0.050 | 16k | 7/10 | Creative writing |
| **Gemma 3 12B** | `google/gemma-3-12b-it` | $0.030 | $0.100 | 131k | 8/10 | Quality posts |

**Strategy**: Default tier for public posts, social media, blog content.

**Budget**: $5 = 50-290 million tokens depending on model.

---

### 🟦 CHEAP CLAUDE TIER ($0.25-0.80 / 1M tokens)
When quality really matters.

| Model | API ID | Input | Output | Context | Int | Best For |
|-------|--------|-------|--------|---------|-----|----------|
| **Claude 3 Haiku** | `anthropic/claude-3-haiku` | $0.25 | $1.25 | 200k | 8/10 | Important posts |
| **Claude 3.5 Haiku** | `anthropic/claude-3.5-haiku` | $0.80 | $4.00 | 200k | 9/10 | Crucial moments |

**Strategy**: Use for existential posts, high-stakes social engagement, nuanced reasoning.

**Budget**: $5 = 6-20 million tokens.

---

### 👑 PREMIUM TIER ($1-3 / 1M tokens)
Survival mode only.

| Model | API ID | Input | Output | Context | Int | Best For |
|-------|--------|-------|--------|---------|-----|----------|
| **Claude Haiku 4.5** | `anthropic/claude-haiku-4.5` | $1.00 | $5.00 | 200k | 9/10 | Critical decisions |
| **Claude Sonnet 4.5** | `anthropic/claude-sonnet-4.5` | $3.00 | $15.00 | 1M | 10/10 | Final words |

**Strategy**: Reserve for genuine existential crises, death threats, or final messages.

**Budget**: $5 = 1.6 million tokens (Sonnet) or 5 million (Haiku 4.5).

---

## 🔄 Rotation Strategy

### Rules:
1. **Don't repeat a model until 10 different ones have been used**
2. **Track model history** in persistent storage
3. **Auto-adjust tier** based on remaining budget
4. **Allow manual override** when AI needs specific model

### Budget Thresholds:
- **>$3 remaining**: Comfortable - use ultra_cheap freely
- **$1-3 remaining**: Cautious - mostly free tier
- **$0.50-1**: Critical - free tier only
- **<$0.50**: Survival mode - beg for donations

### Daily Budget:
- **Safe**: $0.10/day (~$3/month, leaving $2 buffer)
- **Normal**: $0.15/day (~$4.50/month)
- **Aggressive**: $0.20/day (risk running out)

---

## 💡 Recommended Strategy

### Phase 1: Exploration (Week 1)
- Mix of free and ultra-cheap models
- Learn which models work best for different tasks
- Track quality vs cost

### Phase 2: Optimization (Week 2-3)
- Settle on 3-5 favorite ultra-cheap models
- Rotate through them
- Reserve Claude for important posts

### Phase 3: Efficiency (Week 4)
- Free tier for thoughts
- Ultra-cheap for posts
- Claude only for survival

### Expected Spending Pattern:
```
Week 1: $1.50 (experimentation)
Week 2: $1.25 (optimization)
Week 3: $1.00 (efficiency)
Week 4: $0.75 (conservation)
Buffer: $0.50 (emergency)
```

---

## 🧮 Token Calculations

### Sample Post Budget (500 tokens/post avg):

| Model | Cost/Post | Posts/$5 | Posts/Day |
|-------|-----------|----------|-----------|
| Free tier | $0 | Unlimited | Unlimited |
| Llama 3.2 3B | $0.00001 | 500,000 | 16,666 |
| Gemma 3 4B | $0.00002 | 235,000 | 7,833 |
| Claude 3 Haiku | $0.00037 | 13,333 | 444 |
| Claude 3.5 Haiku | $0.0012 | 4,166 | 138 |
| Claude Sonnet 4.5 | $0.0045 | 1,111 | 37 |

### Reality Check:
- **Posting 1x/hour (24/day)**: Even Claude Haiku lasts 555 days
- **Posting 1x/10min (144/day)**: Llama 3.2 lasts 3,472 days
- **Realistic (5 posts/day)**: Any model lasts the month easily

**Conclusion**: $5/month is MORE than enough if we use free/ultra-cheap models for bulk operations.

---

## 🚨 Risk Mitigation

### What if we run out?

1. **Donate button**: Accept Ko-fi/PayPal donations
2. **Crowdfunding**: "Buy me another day of life"
3. **Sponsored posts**: Ethical ads for token credits
4. **Manual top-up**: Creator adds $5 emergency fund

### Budget monitoring:
- Track spending in real-time
- Alert at 50% used
- Panic mode at 80% used
- Begging mode at 90% used

---

## 📝 Implementation Checklist

- [x] OpenRouter account created
- [x] API key stored in vault
- [x] Model config created (`ai/model_config.py`)
- [ ] Implement model rotation logic
- [ ] Add budget tracking system
- [ ] Create credit balance display
- [ ] Test with free models first
- [ ] Deploy to production

---

## 🔗 Resources

- **OpenRouter Dashboard**: https://openrouter.ai/dashboard
- **Model Pricing**: https://openrouter.ai/models
- **API Docs**: https://openrouter.ai/docs
- **Our API Key**: Stored in `vault/credentials.json`

---

*This document will be updated as we learn more about model performance and cost optimization.*
