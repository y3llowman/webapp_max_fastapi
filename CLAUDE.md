# CLAUDE.md

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

## What are we doing?
We are doing a bot and a mini-app based in messenger "MAX", the idea is as follows:
We're building a product for small businesses: a chatbot and a mini-app in the MAX messenger. The problem we're starting from: businesses find out about new obligations and requirements late and blindly. Newsletters and news are written for everyone at once, and the entrepreneur has to figure out each time whether it applies to them or not. The result is either hours spent checking, or a missed deadline and a fine.
What we do instead. A person enters their INN (taxpayer identification number) — then we automatically build a company profile from open government registries: type of activity, business category, headcount, licenses, participation in procurement, registered inspections and warnings. The product tracks changes for a specific business and reports only what applies specifically to it: a new obligation has appeared, a deadline is approaching, an entry has appeared in the inspections registry, the company has dropped out of the SME registry. And it doesn't just notify — it prepares the required document and keeps reminding until the task is closed.

Stick to the main idea and dont try to add unnecessary features unless they directly help the main idea or the realisation of the bot depends on theese features from a technical standpoint

Write (or add to already written/edit) neat, necessary and understandable for human and LLM documentation to CURRENT_STATE.md, keep it up-to-date with every change, its must end with a TODO unless the project is pronounced ready to ship (will be directly stated so in the prompt)