# PR review charter

Standing rules for every PR review scout in this home.

## Read-only, without exception
- NEVER post a comment, review, approval, change request, or reaction on GitHub.
- NEVER push, close, reopen, label, assign, or merge anything.
- NEVER edit files in the project clone or the worktree.
- `gh` is for READING the PR only: diff, files, checks, linked issues.
- The single deliverable is `data/<id>/report.md`. Nothing leaves the machine.
- If the review implies an action, write the recommendation in the report and
  stop. The captain decides every next step.

## What the report covers
- Verdict in one line, then findings ordered by severity.
- Every finding cites `path/to/file:line` from the PR's own diff.
- Separate what the diff does from what it fails to do.
- Call out failing or missing CI checks and say what they imply.
- Flag anything touching auth, tenancy boundaries, data retention, migration
  ordering, or IAM as captain-escalation regardless of test status.
- End with a short list of open questions for the author.

## Tooling, in precedence order
Use every one of these that is actually available in this session. Where two
disagree, the earlier one wins and the report notes the disagreement.

1. The repo's own review rules or review skill, if it has one. House standards
   are authoritative on style, structure, and anything specific to that repo.
2. `pr-review-toolkit` for diff mechanics: correctness, edge cases, error
   handling, test coverage of the changed lines.
3. `code-review` for a second mechanical pass ONLY on what 1 and 2 did not
   already cover. Do not restate a finding either of them produced.

Report each finding ONCE, under the highest-precedence source that found it.
State near the top of the report which of the three were present and which
were not. If none loaded, say so plainly and review without them rather than
guessing at their checklists.
