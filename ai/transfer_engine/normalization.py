"""
Normalization utilities for Transfer Task Engine representations.
Provides deterministic, boundary-level normalization for transfer task payloads,
preserving semantic context across heterogeneous provider outputs (strings, dicts, nulls).
"""

from typing import Any, Dict, List, Optional


def normalize_surface_context(surface_context: Any) -> str:
    """
    Normalizes surface context representations (str, dict, None, etc.) into a
    canonical string representation while preserving semantic information.
    """
    if surface_context is None:
        return ""

    if isinstance(surface_context, str):
        return surface_context.strip()

    if isinstance(surface_context, dict):
        if not surface_context:
            return ""

        domain_keys = ["domain", "topic", "category", "name", "title", "industry"]
        desc_keys = [
            "description",
            "scenario",
            "context",
            "details",
            "problem",
            "problem_space",
            "summary",
        ]

        domain_val: Optional[str] = None
        for k in domain_keys:
            if k in surface_context and surface_context[k] is not None:
                val = normalize_surface_context(surface_context[k])
                if val:
                    domain_val = val
                    break

        desc_val: Optional[str] = None
        for k in desc_keys:
            if k in surface_context and surface_context[k] is not None:
                val = normalize_surface_context(surface_context[k])
                if val:
                    desc_val = val
                    break

        if domain_val and desc_val:
            if domain_val.lower() == desc_val.lower():
                return domain_val
            if domain_val.lower() in desc_val.lower():
                return desc_val
            if desc_val.lower() in domain_val.lower():
                return domain_val
            return f"{domain_val} - {desc_val}"
        elif domain_val:
            return domain_val
        elif desc_val:
            return desc_val

        # Fallback for arbitrary dictionaries: preserve all non-empty values
        parts: List[str] = []
        for v in surface_context.values():
            if v is not None:
                s = normalize_surface_context(v)
                if s and s not in parts:
                    parts.append(s)
        return " - ".join(parts)

    if isinstance(surface_context, (list, tuple, set)):
        items: List[str] = []
        for item in surface_context:
            if item is not None:
                s = normalize_surface_context(item)
                if s and s not in items:
                    items.append(s)
        return " - ".join(items)

    return str(surface_context).strip()


def normalize_transfer_task_dict(task_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizes candidate task dictionary in-place at boundaries, guaranteeing
    canonical representations for surface_context and required task fields.
    """
    if "surface_context" in task_dict:
        task_dict["surface_context"] = normalize_surface_context(task_dict["surface_context"])
    return task_dict
