from pkg import database
from pkg import workflows


class Summarize(workflows.Workflow):
    session = database.Session
