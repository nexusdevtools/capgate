# capgate/brain/recorder.py

import json
import os
import time
from typing import Optional, List
from capgate_types.core.context_types import EventLogEntry
from core.context import AppContext
from core.logger import logger


DEFAULT_OUTPUT_DIR = "/home/nexus/capgate/data/brain_feed"


def export_event_log(
    output_dir: Optional[str] = None,
    filename: Optional[str] = None,
    max_events: Optional[int] = None
):
    """
    Dump the current event log from context into a .jsonl stream file.

    Args:
        output_dir: Where to write the file (default: brain_feed dir)
        filename: Optional filename override
        max_events: Truncate to this many latest events if provided
    """
    ctx = AppContext()
    output_dir = output_dir or DEFAULT_OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    filename = filename or f"event_log_{int(time.time())}.jsonl"
    output_path = os.path.join(output_dir, filename)

    event_slice: List[EventLogEntry] = ctx.event_log[-max_events:] if max_events else ctx.event_log
    if not event_slice:
        logger.warning("⚠️ No events to export. Event log is empty.")
        return

    try:
        with open(output_path, "w") as f:
            for entry in event_slice:
                f.write(json.dumps(entry) + "\n")
        logger.info(f"🧠 Event log exported to {output_path} ({len(event_slice)} events)")
    except Exception as e:
        logger.error(f"❌ Failed to export event log: {e}")


if __name__ == "__main__":
    export_event_log()
