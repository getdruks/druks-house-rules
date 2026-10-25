class HouseRulesError(Exception):
    """The base of every error this package raises."""


class ConfigError(HouseRulesError):
    """The configuration file is missing, malformed, or names something unknown."""
