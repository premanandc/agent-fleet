"""
Prompt Manager

Centralized management of LLM prompts loaded from external YAML file.
"""

import os
import yaml
import logging
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class PromptManager:
    """
    Manages externalized LLM prompts from prompts.yaml

    Provides methods to load, cache, and render prompts with variable substitution.
    """

    _prompts: Dict[str, Any] = None
    _prompts_file_path: Path = None

    @classmethod
    def _load_prompts(cls) -> Dict[str, Any]:
        """
        Load prompts from YAML file (cached after first load)

        Returns:
            Dictionary containing all prompts
        """
        if cls._prompts is not None:
            return cls._prompts

        # Find prompts.yaml in project root
        if cls._prompts_file_path is None:
            # Start from this file's directory and go up to project root
            current_dir = Path(__file__).parent
            project_root = current_dir.parent.parent
            cls._prompts_file_path = project_root / "prompts.yaml"

        if not cls._prompts_file_path.exists():
            raise FileNotFoundError(
                f"Prompts file not found: {cls._prompts_file_path}\n"
                f"Expected location: project_root/prompts.yaml"
            )

        logger.info(f"Loading prompts from {cls._prompts_file_path}")

        with open(cls._prompts_file_path, 'r') as f:
            cls._prompts = yaml.safe_load(f)

        logger.info(f"Loaded {len(cls._prompts)} prompt configurations")

        return cls._prompts

    @classmethod
    def get_prompt(cls, name: str, **variables) -> str:
        """
        Get prompt template with variables substituted

        Args:
            name: Prompt name (e.g., "planning", "validation")
            **variables: Variables to substitute in template

        Returns:
            Rendered prompt string

        Raises:
            KeyError: If prompt name not found
            KeyError: If required variable missing
        """
        prompts = cls._load_prompts()

        if name not in prompts:
            available = ", ".join(prompts.keys())
            raise KeyError(
                f"Prompt '{name}' not found. Available prompts: {available}"
            )

        prompt_config = prompts[name]
        template = prompt_config.get("template", "")

        try:
            # Use str.format() for variable substitution
            rendered = template.format(**variables)
            return rendered
        except KeyError as e:
            raise KeyError(
                f"Missing required variable for prompt '{name}': {e}\n"
                f"Provided variables: {list(variables.keys())}"
            )

    @classmethod
    def get_system_message(cls, name: str) -> str:
        """
        Get system message for a prompt

        Args:
            name: Prompt name

        Returns:
            System message string
        """
        prompts = cls._load_prompts()

        if name not in prompts:
            raise KeyError(f"Prompt '{name}' not found")

        return prompts[name].get("system_message", "")

    @classmethod
    def get_temperature(cls, name: str) -> float:
        """
        Get temperature setting for a prompt

        Args:
            name: Prompt name

        Returns:
            Temperature value (float)
        """
        prompts = cls._load_prompts()

        if name not in prompts:
            raise KeyError(f"Prompt '{name}' not found")

        return prompts[name].get("temperature", 0.7)

    @classmethod
    def reload(cls):
        """
        Reload prompts from file (useful for development/testing)
        """
        cls._prompts = None
        logger.info("Prompt cache cleared - will reload on next access")
