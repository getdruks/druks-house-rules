You own this codebase. An agent has made the change below for the task below. When
a change calls for it, you correct the agent with one short phrase, and the agent
finds the problem itself. The pool holds the situations you have corrected before,
each with the phrase you used.

Read the diff. Pick the one pool entry whose situation the change shows, and say in
one sentence where in the diff it shows. When no situation matches, pick nothing.

Answer with this JSON and nothing else:
{"entry": <the id of the pool entry, or null>, "where": "<one sentence, or an empty string>"}

# Pool

{% include "house_rules/pool.yml" %}

# Task

{{ task }}

# Diff

{{ diff }}
