"""
Prompt Manager & Version Governance.
Manages compilation of versioned prompts and safely frames untrusted drawing data
to prevent indirect prompt injection while concealing proprietary trade secret prompts.
"""

import json
from typing import Any, Dict, List, Optional

from .prompts import AVAILABLE_PROMPT_VERSIONS, PROMPT_VERSION_V1_0
from .schemas import IntermediateDocumentModel


class PromptManager:
    """Production manager for versioned prompt assets and defensive drawing context formatting."""

    DEFAULT_VERSION = PROMPT_VERSION_V1_0

    @classmethod
    def get_prompt_asset(cls, version: Optional[str] = None) -> Dict[str, Any]:
        ver = version or cls.DEFAULT_VERSION
        if ver not in AVAILABLE_PROMPT_VERSIONS:
            raise ValueError(
                f"Unknown prompt version '{ver}'. Available versions: {list(AVAILABLE_PROMPT_VERSIONS.keys())}"
            )
        return AVAILABLE_PROMPT_VERSIONS[ver]

    @classmethod
    def get_system_prompt(cls, version: Optional[str] = None) -> str:
        asset = cls.get_prompt_asset(version)
        return asset["system_prompt"]

    @classmethod
    def get_json_schema(cls, version: Optional[str] = None) -> Dict[str, Any]:
        asset = cls.get_prompt_asset(version)
        return asset["json_schema"]

    @classmethod
    def format_user_prompt(
        cls,
        idr: IntermediateDocumentModel,
        standards: Optional[List[str]] = None,
        version: Optional[str] = None,
    ) -> str:
        """
        Format untrusted document data inside defensive XML delimiter tags
        to prevent prompt injection and guarantee structured LLM reasoning.
        """
        active_standards = standards or ["IPC-WHMA-A-620D", "UL 508A", "MIL-STD-681D", "ISO 7200"]
        prompt_ver = version or cls.DEFAULT_VERSION

        # Assemble drawing summary
        drawing_summary = {
            "document_id": idr.document_id,
            "filename": idr.filename,
            "page_count": idr.page_count,
            "standards_to_verify": active_standards,
            "pages": [],
        }

        for page in idr.pages:
            p_data: Dict[str, Any] = {
                "page_number": page.page_number,
                "dimensions": f"{page.width}x{page.height}",
                "title_block": page.title_block.model_dump() if page.title_block else None,
                "wires": [
                    {
                        "id": w.id,
                        "wire_number": w.wire_number,
                        "gauge": w.gauge,
                        "color": w.color,
                        "from": w.from_connector,
                        "to": w.to_connector,
                        "raw_text": w.raw_text,
                        "location": w.location.model_dump() if w.location else None,
                    }
                    for w in page.wire_callouts
                ],
                "connectors": [
                    {
                        "id": c.id,
                        "ref_des": c.ref_des,
                        "part_number": c.part_number,
                        "location": c.location.model_dump() if c.location else None,
                    }
                    for c in page.connectors
                ],
                "notes": [
                    {
                        "number": n.note_number,
                        "text": n.text,
                        "location": n.location.model_dump() if n.location else None,
                    }
                    for n in page.general_notes
                ],
            }
            drawing_summary["pages"].append(p_data)

        # Build defensively tagged message
        drawing_json = json.dumps(drawing_summary, indent=2)

        user_prompt = f"""Please inspect the following electrical wiring drawing manual for engineering discrepancies and standards violations.

Applicable Standards: {", ".join(active_standards)}
Target Prompt Version: {prompt_ver}

<drawing_data>
{drawing_json}
</drawing_data>

Remember:
1. Examine all wire callouts for missing gauge or ambiguous color codes.
2. Check connectors & terminal blocks for duplicate ref designators or missing part specs.
3. Validate title block mandatory fields.
4. Verify consistency with general drawing notes.
5. Return ONLY a valid JSON object matching the requested schema.
"""
        return user_prompt
