This file add a list of useful prompts outside the agents.

# Self improvement prompt

## Aim

Improve the process of building new entries in theoria-dataset by analyzing the mistakes made by the agents and proposing fixes to both the process and the entries themselves.

## Prompt

The theoria-agents have built the entry named in the end. This is the list of problems or mistakes that the agents did:

- xxxxxxxxxxxxx
- yyyyyyyyyyyyy

Analyze the problems. Look at the principles stated in the md files of theoria-agents and theoria-dataset. You can also look to the logs

When there is an issue that can be fixed by modifying the CONTRIBUTING.md of theoria-dataset, start there. We don't want to add prompting to the agents if it can be fixed in the single source of true place.

Build an implementation plan with the objective of ensuring the issue does not repeat in the future generation of entries.

Add to the plan the fixes that needs to be done to the entry itself.

Entry name:
[ENTRY NAME]
