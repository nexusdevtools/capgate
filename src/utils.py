# src/core/utils.py

import re

def render_template(template_str: str, replacements: dict) -> str:
    for key, val in replacements.items():
        template_str = template_str.replace(key, val)
    return template_str

def sanitize_plugin_name(name: str) -> str:
    """
    Sanitize a plugin name to be a valid Python identifier.

    - Lowercase
    - Replace spaces and hyphens with underscores
    - Remove invalid characters
    - Ensure it starts with a letter or underscore

    Args:
        name (str): Raw plugin name input

    Returns:
        str: Sanitized plugin name
    """
    name = name.lower().strip()
    name = re.sub(r'[\s\-]+', '_', name)         # Replace space and hyphen with _
    name = re.sub(r'\W|^(?=\d)', '_', name)      # Replace non-word chars & leading digit
    return name
