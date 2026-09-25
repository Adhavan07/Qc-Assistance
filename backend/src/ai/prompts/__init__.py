"""
Versioned AI Prompt Assets.
Houses proprietary client-validated prompt templates.
Maintained strictly server-side and never exposed to client browsers or API payloads.
"""

from .wiring_qc_v1_0 import (
    PROMPT_VERSION as PROMPT_VERSION_V1_0,
    SYSTEM_PROMPT as SYSTEM_PROMPT_V1_0,
    JSON_OUTPUT_SCHEMA as JSON_OUTPUT_SCHEMA_V1_0,
)

AVAILABLE_PROMPT_VERSIONS = {
    PROMPT_VERSION_V1_0: {
        "system_prompt": SYSTEM_PROMPT_V1_0,
        "json_schema": JSON_OUTPUT_SCHEMA_V1_0,
        "description": "Validated baseline electrical wiring diagram inspection prompt",
    }
}
