"""Typed application errors and stable command exit codes."""

from __future__ import annotations


class CardAssistantError(RuntimeError):
    """Base error carrying the CLI exit code for this failure class."""

    exit_code = 2


class InputError(CardAssistantError):
    """Broken or missing user input."""

    exit_code = 2


class ConfigurationError(CardAssistantError):
    """Missing or invalid local LLM configuration."""

    exit_code = 3


class LlmError(CardAssistantError):
    """Base class for remote LLM failures."""

    exit_code = 4


class ApiError(LlmError):
    """API, network or proxy failure."""

    exit_code = 4


class ResultError(LlmError):
    """The model returned an unusable or invalid result."""

    exit_code = 5
