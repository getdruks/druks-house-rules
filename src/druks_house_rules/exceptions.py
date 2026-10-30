class HouseRulesError(Exception):
    """The base of every error this package raises."""


class ConfigError(HouseRulesError):
    """The configuration file is missing, malformed, or names something unknown."""


class MissingConfigError(ConfigError):
    """The configuration file is not in the repository."""


class UnknownEntryError(HouseRulesError):
    """The model picked an entry id that the pool does not hold."""
