# Workflow: Draft a stakeholder / client reply

**Tier:** standard @ medium (accuracy gate: never the light tier — it is external text).
**Input:** item ID. **Output:** a draft for the developer to review; agents never post.

1. Load the item, its category, and the team's fix lifecycle status. Read the
   bugs-and-fixes export if present — the reply must agree with it.
2. Choose the reply shape by category × status:
   - defect, fixed/deployed → cause (plain language), fix, where/when to retest;
   - defect, in progress → acknowledgement + current finding + next step;
   - works-as-designed → the designed behavior, cited from spec/reference, and the
     alternative if the stakeholder wants a change (becomes a change request);
   - question → direct answer; request → scope confirmation;
   - cannot reproduce → what was tried, exact record/env, what is needed.
3. Where the process requires it, state **both** the technical cause and the
   underlying cause (why it happened: port regression, spec gap, uncovered edge case).
4. Write in the stakeholder's language and register (configure
   `stakeholder.language` / `stakeholder.register`); keep UI labels verbatim.
5. Always add a faithful translation for the developer if the reply language differs.
6. Flag for review: claims that need confirmation, commitments on dates, anything
   that reads as blame. No internal names, no file paths, no credentials.
