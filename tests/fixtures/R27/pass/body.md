Adds the `druks-house-rules check` command.

The check reads the files the working tree changes against the merge base and runs each rule over them. ruff runs once for the three rules it owns; the syntax rules read one parsed tree per file.
