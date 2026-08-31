"""
YAML Frontmatter Formatter and Parser
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Tuple


FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def format_frontmatter(metadata: Dict[str, Any]) -> str:
    """Serialize a dictionary into standard YAML frontmatter block"""
    lines = ["---"]
    for k, v in metadata.items():
        if v is None:
            continue
        if isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        elif isinstance(v, (int, float)):
            lines.append(f"{k}: {v}")
        elif isinstance(v, list):
            if not v:
                lines.append(f"{k}: []")
            elif all(isinstance(x, (str, int, float)) for x in v):
                lines.append(f"{k}:")
                for x in v:
                    lines.append(f"  - {x}")
            else:
                lines.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
        elif isinstance(v, dict):
            lines.append(f"{k}:")
            for dk, dv in v.items():
                lines.append(f"  {dk}: {dv}")
        else:
            # String handling
            val_str = str(v).replace('"', '\\"')
            if "\n" in val_str or ":" in val_str or "#" in val_str:
                lines.append(f'{k}: "{val_str}"')
            else:
                lines.append(f"{k}: {val_str}")
    lines.append("---")
    return "\n".join(lines)


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter and return (metadata_dict, remaining_markdown_body)"""
    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        return {}, content

    yaml_block = match.group(1)
    body = content[match.end():]
    metadata: Dict[str, Any] = {}

    current_key = None
    in_list = False

    for line in yaml_block.split("\n"):
        line_str = line.rstrip()
        if not line_str or line_str.startswith("#"):
            continue

        # Check list item
        if line_str.startswith("  - ") or line_str.startswith("    - "):
            val = line_str.split("- ", 1)[1].strip().strip('"').strip("'")
            if current_key and in_list:
                metadata[current_key].append(val)
            continue

        if ":" in line_str:
            parts = line_str.split(":", 1)
            key = parts[0].strip()
            val = parts[1].strip()

            if val == "":
                # Could be starting a list
                current_key = key
                in_list = True
                metadata[key] = []
            elif val.startswith("[") and val.endswith("]"):
                # Inline list
                current_key = key
                in_list = False
                try:
                    metadata[key] = json.loads(val)
                except Exception:
                    metadata[key] = [x.strip().strip('"').strip("'") for x in val[1:-1].split(",") if x.strip()]
            elif val.lower() == "true":
                metadata[key] = True
                current_key = key
                in_list = False
            elif val.lower() == "false":
                metadata[key] = False
                current_key = key
                in_list = False
            elif val.isdigit():
                metadata[key] = int(val)
                current_key = key
                in_list = False
            else:
                metadata[key] = val.strip('"').strip("'")
                current_key = key
                in_list = False

    return metadata, body
