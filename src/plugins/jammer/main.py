"""
${plugin_name}.py — Auto-generated CapGate plugin
Created on ${created_at}
Author: ${author}
"""

from core.context import AppContext
from core.logger import logger

from typing import Any

def run(ctx: AppContext, *args: Any, **kwargs: Any):
    logger.info("Running ${plugin_name} plugin...")
    logger.info(f"Available interfaces: {ctx.get('interfaces')}")
    logger.info(f"Args: {args} | Kwargs: {kwargs}")
    # Your logic here