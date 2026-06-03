---
description: Deep research over Tornix PMO data and/or the web, then synthesize a cited answer.
argument-hint: "<question>" [--project <id>] [--source pmo|web|both]
---

You are running Tornix deep-research.

1. Run: `tornix --json deep-research $ARGUMENTS` (defaults to `--source pmo`).
2. The CLI returns `{question, sub_questions, corpus, web_brief, instructions}`.
3. If `web_brief` is present, execute its `search_queries` with your own web tools.
4. Synthesize a cited answer: cite PMO facts by their `citation` (`tornix://kind/id`);
   cite web facts by URL. Address each sub-question. Surface blockers and next actions.
5. Present a concise report with a citations list.
