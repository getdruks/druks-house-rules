from druks.apps import App


class HouseRules(App):
    name = "house_rules"
    icon = "gavel"
    description = (
        "Runs druks-house-rules on each pull request head and posts the findings "
        "as the druks-house-rules check run."
    )
