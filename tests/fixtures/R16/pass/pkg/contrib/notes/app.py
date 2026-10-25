from pkg import db
from pkg import workflows


class Summarize(workflows.Workflow):
    model = db.Model
