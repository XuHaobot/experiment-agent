"""
Obsidian Vault Bridge Subsystem
"""
from backend.vault.models import (
    VaultExportOptions,
    VaultFileAction,
    VaultPreviewSummary,
    VaultReconcileStatus,
)
from backend.vault.frontmatter import (
    format_frontmatter,
    parse_frontmatter,
)
from backend.vault.wikilinks import (
    wikilink,
    extract_wikilinks,
)
from backend.vault.renderer import (
    START_TAG,
    END_TAG,
    merge_with_existing,
    render_project,
    render_question,
    render_hypothesis,
    render_experiment,
    render_evidence,
    render_conclusion,
    render_paper,
    render_artifact,
)
from backend.vault.manifest import (
    load_manifest,
    save_manifest,
    get_manifest_path,
)
from backend.vault.exporter import (
    preview_vault_export,
    export_project_to_vault,
)
from backend.vault.importer import (
    reconcile_vault,
)

__all__ = [
    "VaultExportOptions",
    "VaultFileAction",
    "VaultPreviewSummary",
    "VaultReconcileStatus",
    "format_frontmatter",
    "parse_frontmatter",
    "wikilink",
    "extract_wikilinks",
    "START_TAG",
    "END_TAG",
    "merge_with_existing",
    "render_project",
    "render_question",
    "render_hypothesis",
    "render_experiment",
    "render_evidence",
    "render_conclusion",
    "render_paper",
    "render_artifact",
    "load_manifest",
    "save_manifest",
    "get_manifest_path",
    "preview_vault_export",
    "export_project_to_vault",
    "reconcile_vault",
]
