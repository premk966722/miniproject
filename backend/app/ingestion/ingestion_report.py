from __future__ import annotations

from typing import Any, Dict, List


def build_ingestion_report(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(results)
    changed = sum(1 for item in results if item.get("changed") is True)
    unchanged = sum(1 for item in results if item.get("status") == "unchanged")
    successful = sum(1 for item in results if item.get("status") == "success")
    failed = sum(1 for item in results if item.get("status") == "error")
    return {
        "total_sources_processed": total,
        "successful_ingestions": successful,
        "unchanged_documents": unchanged,
        "changed_documents": changed,
        "failed_sources": failed,
        "source_statuses": {item.get("source_id", "unknown"): item.get("status", "unknown") for item in results},
        "results": results,
    }
