"""Mutating filesystem actions — organise, de-duplicate, clean downloads.

This module does the *dangerous* work behind ``POST /api/files/organise``
and ``POST /api/files/clean/{duplicates,downloads}``.  Everything here is
plain filesystem code: no FastAPI, no database, no ``app.state`` — so the
safety rules can be unit-tested against a fabricated tree under ``tmp_path``.

Safety model
------------
1. **Dry run by default.**  Every planner returns a complete manifest and
   touches nothing.  The router only calls :func:`execute_plan` when the
   request body carried ``confirm: true``.
2. **Root confinement.**  Both the source and the destination of every
   operation are ``Path.resolve()``-d (following symlinks, collapsing
   ``..``) and must land inside an allowed root.  Anything else is refused
   — see :func:`resolve_within`.
3. **Symlinks are never followed.**  ``os.walk`` runs with
   ``followlinks=False`` and symlinked files are skipped outright, so a
   link can never be used to reach outside the roots and a "delete" can
   never destroy a link's target.
4. **Protected trees are never entered**: ``.git``, ``node_modules``,
   ``__pycache__``, ``.venv``, every dot-directory, and the configured
   projects root.
5. **Deletion means the XDG trash.**  A file is moved into the freedesktop
   trash (``~/.local/share/Trash`` by default, overridable in config).
   When the trash is unusable — most commonly because the file lives on a
   different filesystem — the operation is *skipped* unless the request
   sets ``force_delete: true`` **and** config allows
   ``allow_permanent_delete``.  Even then, nothing is ever unlinked
   without appearing in the manifest first.
6. **Never overwrite.**  A destination that already exists is skipped with
   a reason.  The move itself reserves the destination with
   ``O_CREAT|O_EXCL`` so the check-then-rename race cannot clobber a file.
7. **Plans are computed from the live filesystem**, never from the stored
   audit — acting on a stale scan could move a file that has since changed.

PDF routing heuristic
---------------------
See :func:`classify_pdf`.  Deliberately simple and biased towards
``Documents/``: a PDF is only called a book when there is positive
evidence, and any document-ish filename marker wins immediately.
"""

from __future__ import annotations

import errno
import logging
import os
import re
import shutil
from collections import defaultdict
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

from sysadmin.core.config import FileActionsConfig, FileOrganiserConfig
from sysadmin.core.contracts import FileActionResponse, FileFlag, FileOperation
from sysadmin.files.agent import FILE_CATEGORIES, file_hash

logger = logging.getLogger(__name__)

# Directory names never entered, whatever the config says.  These are
# either version control, build/venv detritus, or private config.
PROTECTED_DIR_NAMES = frozenset({
    ".git", ".svn", ".hg", ".bzr",
    "node_modules", "__pycache__", ".venv", "venv", ".tox",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".cache", ".config", ".local", ".ssh", ".gnupg",
    "site-packages", ".Trash", "Trash",
})

# Duplicate detection ignores anything smaller than this (matches the agent).
MIN_DUPLICATE_BYTES = 1024

DUPLICATE_STRATEGIES = ("newest", "largest")
DOWNLOAD_MODES = ("archive", "trash")


class FileActionError(Exception):
    """A request the action layer refuses outright — mapped to HTTP 4xx."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


class PathEscapeError(FileActionError):
    """A path resolved outside every allowed root."""

    def __init__(self, path: Path | str) -> None:
        super().__init__(
            f"refusing to operate on {path}: resolves outside the allowed roots",
            status_code=400,
        )


# ── Root confinement ─────────────────────────────────────────────────


def resolve_within(path: Path | str, roots: list[Path]) -> Path:
    """Resolve ``path`` fully and assert it is inside one of ``roots``.

    Resolution happens *before* the check so ``..`` segments and symlinks
    cannot be used to step outside.  Works for paths that do not exist yet
    (destinations), since ``Path.resolve()`` is non-strict.

    Raises:
        PathEscapeError: the resolved path is outside every root.
    """
    resolved = Path(path).resolve()
    for root in roots:
        if resolved == root or root in resolved.parents:
            return resolved
    raise PathEscapeError(path)


def is_within(path: Path, roots: list[Path]) -> bool:
    """Non-raising form of :func:`resolve_within`."""
    try:
        resolve_within(path, roots)
    except PathEscapeError:
        return False
    return True


def _skip_directory(
    dirpath: Path,
    name: str,
    skip_dirs: set[str],
    excluded_roots: list[Path],
) -> bool:
    """Should ``os.walk`` prune this directory?"""
    if name.startswith(".") or name in PROTECTED_DIR_NAMES or name in skip_dirs:
        return True
    if dirpath.is_symlink():
        return True
    resolved = dirpath.resolve()
    return any(resolved == ex or ex in resolved.parents for ex in excluded_roots)


def walk_files(
    root: Path,
    skip_dirs: set[str],
    excluded_roots: list[Path],
) -> Iterator[Path]:
    """Yield regular, non-symlink, non-hidden files under ``root``.

    Prunes protected/skipped/excluded directories and never follows
    symlinked directories (``followlinks=False``).
    """
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        here = Path(dirpath)
        dirnames[:] = [
            d for d in dirnames
            if not _skip_directory(here / d, d, skip_dirs, excluded_roots)
        ]
        for name in filenames:
            if name.startswith("."):
                continue
            candidate = here / name
            if candidate.is_symlink():
                continue
            try:
                if not candidate.is_file():
                    continue
            except OSError:
                continue
            yield candidate


# ── The XDG trash ────────────────────────────────────────────────────


def trash_root_for(home: Path, configured: str | None = None) -> Path:
    """Where the freedesktop trash lives.

    Defaults to ``<home>/.local/share/Trash`` (the spec's default for
    ``$XDG_DATA_HOME/Trash``).  No environment variable is read — this
    project takes all settings from ``config.yaml`` — so a non-standard
    data home is expressed with ``agents.file_organiser.actions.trash_dir``.
    """
    if configured:
        return Path(configured).expanduser()
    return home / ".local" / "share" / "Trash"


def trash_is_usable(path: Path, trash_root: Path) -> bool:
    """Can ``path`` be trashed by a rename into ``trash_root``?

    The freedesktop home trash only accepts files on its own filesystem;
    anything else would need a copy+unlink (i.e. a real delete), which we
    refuse to do implicitly.
    """
    try:
        files_dir = trash_root / "files"
        files_dir.mkdir(parents=True, exist_ok=True)
        return os.stat(files_dir).st_dev == os.lstat(path).st_dev
    except OSError:
        return False


def send_to_trash(path: Path, trash_root: Path) -> Path:
    """Move ``path`` into the XDG trash, writing its ``.trashinfo`` record.

    Uses ``os.rename``, so a symlink is moved as a link and its target is
    untouched.  Returns the path inside the trash.
    """
    files_dir = trash_root / "files"
    info_dir = trash_root / "info"
    files_dir.mkdir(parents=True, exist_ok=True)
    info_dir.mkdir(parents=True, exist_ok=True)

    stem, suffix = path.stem, path.suffix
    name = path.name
    counter = 1
    while (files_dir / name).exists() or (info_dir / f"{name}.trashinfo").exists():
        name = f"{stem}.{counter}{suffix}"
        counter += 1

    info_path = info_dir / f"{name}.trashinfo"
    deleted_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    # Write the info record first: a trashed file with no record is much
    # worse than a stale record with no file.
    info_path.write_text(
        "[Trash Info]\n"
        f"Path={quote(str(path))}\n"
        f"DeletionDate={deleted_at}\n"
    )
    destination = files_dir / name
    try:
        os.rename(path, destination)
    except OSError:
        info_path.unlink(missing_ok=True)
        raise
    return destination


def _safe_move(source: Path, destination: Path) -> None:
    """Move ``source`` → ``destination``, never overwriting.

    ``os.rename`` silently clobbers an existing destination on POSIX, so
    the destination is first reserved atomically with ``O_CREAT|O_EXCL``;
    losing that race raises ``FileExistsError`` instead of destroying a
    file.  Falls back to copy+unlink only across filesystems.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        os.rename(source, destination)
    except OSError as exc:
        if getattr(exc, "errno", None) != errno.EXDEV:
            destination.unlink(missing_ok=True)
            raise
        shutil.copy2(source, destination)
        os.unlink(source)


# ── Categorisation ───────────────────────────────────────────────────

# Filenames that all but guarantee a PDF is paperwork, not a book.
_DOCUMENT_MARKERS = re.compile(
    r"invoice|receipt|statement|payslip|payment|bill|contract|letter|cv|"
    r"resume|form|ticket|boarding|order|quote|tax|p60|p45|certificate|"
    r"report|minutes|agenda|slides|presentation",
    re.IGNORECASE,
)
# Filenames that suggest a book.
_BOOK_MARKERS = re.compile(
    r"\bbook\b|chapter|\bvol(?:ume)?[\s._-]*\d|edition|manual|handbook|"
    r"textbook|cookbook|\bpress\b|oreilly|o'reilly|packt|manning|"
    r"z-?lib(?:rary)?|libgen|anna'?s[\s._-]*archive|"
    r"\b(?:97[89][\d-]{10,})\b|\bisbn\b",
    re.IGNORECASE,
)
# ``/Count`` also appears on ``/Type /Outlines`` nodes, so only accept one
# that sits in the same dictionary as ``/Type /Pages`` (either order).
_PDF_COUNT_RE = re.compile(
    rb"/Type\s*/Pages[^>]{0,200}?/Count\s+(\d+)"
    rb"|/Count\s+(\d+)[^>]{0,200}?/Type\s*/Pages"
)
_PDF_WINDOW_BYTES = 1024 * 1024


def pdf_page_count(path: Path) -> int | None:
    """Cheap, best-effort PDF page count — ``None`` when undetermined.

    Reads at most 1 MB from each end of the file and looks for a
    ``/Count n`` sitting in a ``/Type /Pages`` dictionary (the page tree).
    Sub-trees carry partial counts, so the largest match wins.

    Deliberately does not parse the PDF: this is a routing hint, and
    "unknown" is a perfectly good answer that simply makes the caller fall
    through to the conservative default.
    """
    try:
        size = path.stat().st_size
        with open(path, "rb") as handle:
            head = handle.read(_PDF_WINDOW_BYTES)
            if size > _PDF_WINDOW_BYTES:
                handle.seek(max(0, size - _PDF_WINDOW_BYTES))
                tail = handle.read(_PDF_WINDOW_BYTES)
            else:
                tail = b""
    except OSError:
        return None

    counts = [
        int(match.group(1) or match.group(2))
        for chunk in (head, tail)
        for match in _PDF_COUNT_RE.finditer(chunk)
    ]
    plausible = [c for c in counts if 0 < c < 100_000]
    return max(plausible) if plausible else None


def classify_pdf(path: Path, config: FileActionsConfig) -> tuple[str, str]:
    """Route a PDF to ``books`` or ``documents``. Returns (category, why).

    The heuristic, in order — first match wins:

    1. Filename carries a paperwork marker (invoice, receipt, payslip, …)
       → ``documents``.
    2. Filename carries a book marker (ISBN, "chapter", "vol. 2",
       "edition", a publisher name, …) → ``books``.
    3. A page count could be read cheaply and is ≥ ``pdf_book_min_pages``
       → ``books``.
    4. Otherwise → ``documents``.

    Note rule 3 needs *positive* evidence: an undetermined page count
    never routes to ``books``.  File size alone is not enough either — a
    single scanned page can be tens of megabytes.  When unsure we always
    prefer ``documents``, because a misfiled document is a nuisance while
    a misfiled book is the same nuisance plus a surprise.
    """
    name = path.name
    if _DOCUMENT_MARKERS.search(name):
        return "documents", "filename matches a document marker"
    if _BOOK_MARKERS.search(name):
        return "books", "filename matches a book marker"

    pages = pdf_page_count(path)
    if pages is not None and pages >= config.pdf_book_min_pages:
        return "books", f"page count {pages} >= {config.pdf_book_min_pages}"

    try:
        size_mb = path.stat().st_size / (1024 * 1024)
    except OSError:
        size_mb = 0.0
    if pages is not None and size_mb >= config.pdf_book_min_mb:
        return (
            "documents",
            f"only {pages} pages despite {size_mb:.1f}MB — treated as a document",
        )
    return "documents", "no book evidence — conservative default"


def category_for(path: Path) -> str | None:
    """Which :data:`FILE_CATEGORIES` bucket an extension belongs to."""
    ext = path.suffix.lower()
    for category, spec in FILE_CATEGORIES.items():
        if ext in spec["extensions"]:
            return category
    return None


def _in_expected_place(
    path: Path,
    root: Path,
    category: str,
    destination_dir: Path,
) -> bool:
    """Is the file already filed correctly?

    True when it sits under the configured destination, or under any of
    the category's traditional folder names (so an existing ``photos/``
    tree is not churned into ``Pictures/``).
    """
    resolved = path.resolve()
    if destination_dir == resolved.parent or destination_dir in resolved.parents:
        return True
    expected = FILE_CATEGORIES.get(category, {}).get("expected_dirs", set())
    try:
        parts = resolved.relative_to(root).parts[:-1]
    except ValueError:
        return False
    return any(part in expected for part in parts)


def _destination_dir(
    root: Path,
    category: str,
    config: FileActionsConfig,
) -> Path | None:
    """Resolve a category's configured folder to an absolute path."""
    folder = config.category_folders.get(category)
    if not folder:
        return None
    candidate = Path(folder).expanduser()
    return candidate if candidate.is_absolute() else root / candidate


# ── Planning ─────────────────────────────────────────────────────────


def _new_response(operation: str, root: Path, dry_run: bool) -> FileActionResponse:
    return FileActionResponse(
        operation=operation,
        dry_run=dry_run,
        scan_root=str(root),
    )


def _finalise(response: FileActionResponse) -> FileActionResponse:
    """Recompute the summary counters from the manifest."""
    response.planned_count = sum(1 for o in response.operations if o.status == "planned")
    response.done_count = sum(1 for o in response.operations if o.status == "done")
    response.skipped_count = sum(1 for o in response.operations if o.status == "skipped")
    response.failed_count = sum(1 for o in response.operations if o.status == "failed")
    response.total_bytes = sum(
        o.size_bytes for o in response.operations if o.status in ("planned", "done")
    )
    return response


def _size_of(path: Path) -> int:
    try:
        return path.lstat().st_size
    except OSError:
        return 0


def plan_organise(
    organiser: FileOrganiserConfig,
    excluded_roots: list[Path],
    categories: list[str] | None = None,
) -> FileActionResponse:
    """Plan the relocation of misplaced files into their category folders.

    Loose code files in the scan root are *flagged only* — never moved.
    A file in the home root usually means work in progress, and moving it
    would be actively unhelpful.
    """
    config = organiser.actions
    root = Path(organiser.scan_root).expanduser().resolve()
    roots = [root]
    skip_dirs = set(organiser.skip_dirs)
    wanted = set(categories) if categories else None
    code_exts = {e.lower() for e in config.code_extensions}

    response = _new_response("organise", root, dry_run=True)
    if not root.is_dir():
        response.message = f"scan root {root} does not exist"
        return _finalise(response)

    for path in walk_files(root, skip_dirs, excluded_roots):
        if len(response.operations) >= config.max_operations:
            response.truncated = True
            break

        # Loose code in the scan root itself → flag, never move.
        if path.parent == root and path.suffix.lower() in code_exts:
            response.flagged.append(FileFlag(
                path=str(path),
                kind="loose_code",
                reason="code file in the scan root — review manually, never auto-moved",
                size_bytes=_size_of(path),
            ))
            continue

        category = category_for(path)
        if category is None:
            continue

        note: str | None = None
        if path.suffix.lower() == ".pdf":
            category, note = classify_pdf(path, config)

        if wanted is not None and category not in wanted:
            continue

        destination_dir = _destination_dir(root, category, config)
        if destination_dir is None:
            continue

        try:
            destination_dir = resolve_within(destination_dir, roots)
        except PathEscapeError:
            response.operations.append(FileOperation(
                action="move",
                source=str(path),
                category=category,
                size_bytes=_size_of(path),
                status="skipped",
                reason=(
                    f"configured folder for '{category}' resolves outside "
                    f"the scan root"
                ),
            ))
            continue

        if _in_expected_place(path, root, category, destination_dir):
            continue

        destination = destination_dir / path.name
        operation = FileOperation(
            action="move",
            source=str(path),
            destination=str(destination),
            category=category,
            size_bytes=_size_of(path),
            reason=note,
        )
        if destination.exists() or destination.is_symlink():
            operation.status = "skipped"
            operation.reason = "destination already exists — not overwriting"
        response.operations.append(operation)

    return _finalise(response)


def plan_duplicate_cleanup(
    organiser: FileOrganiserConfig,
    excluded_roots: list[Path],
    strategy: str | None = None,
) -> FileActionResponse:
    """Plan removal of duplicate copies, retaining exactly one per group.

    Reuses the agent's ``file_hash`` (size + MD5 of the first 1 MB) so the
    grouping matches what ``/api/files/duplicates`` reports.

    Strategy ``newest`` retains the most recently modified copy,
    ``largest`` the biggest; ties break on the shortest path, then
    lexicographically, so the plan is deterministic.
    """
    config = organiser.actions
    strategy = strategy or config.duplicate_strategy
    if strategy not in DUPLICATE_STRATEGIES:
        raise FileActionError(
            f"unknown strategy {strategy!r}; expected one of "
            f"{', '.join(DUPLICATE_STRATEGIES)}"
        )

    root = Path(organiser.scan_root).expanduser().resolve()
    skip_dirs = set(organiser.skip_dirs)
    response = _new_response("clean_duplicates", root, dry_run=True)
    if not root.is_dir():
        response.message = f"scan root {root} does not exist"
        return _finalise(response)

    groups: dict[str, list[Path]] = defaultdict(list)
    for path in walk_files(root, skip_dirs, excluded_roots):
        size = _size_of(path)
        if size < MIN_DUPLICATE_BYTES:
            continue
        digest = file_hash(path, size)
        if digest:
            groups[digest].append(path)

    for digest, members in sorted(groups.items()):
        if len(members) < 2:
            continue
        if len(response.operations) >= config.max_operations:
            response.truncated = True
            break

        keeper = _pick_keeper(members, strategy)
        removals = [p for p in members if p != keeper]

        # Invariant: exactly one copy survives every group.  A bug here
        # would delete the user's only copy, so it is checked rather than
        # assumed (and again in execute_plan).
        if len(removals) != len(members) - 1 or keeper in removals:
            raise RuntimeError(
                f"duplicate group {digest} would not retain exactly one copy"
            )

        for path in removals:
            response.operations.append(FileOperation(
                action="trash",
                source=str(path),
                size_bytes=_size_of(path),
                reason=f"duplicate ({strategy} copy retained)",
                keep_path=str(keeper),
            ))

    response.message = f"retaining the {strategy} copy of each duplicate group"
    return _finalise(response)


def _pick_keeper(members: list[Path], strategy: str) -> Path:
    """Choose the single copy to retain from a duplicate group."""
    def sort_key(path: Path) -> tuple:
        try:
            stat = path.lstat()
            primary = stat.st_mtime if strategy == "newest" else stat.st_size
        except OSError:
            primary = 0
        # Negated primary → the newest/largest sorts first; then the
        # shortest path, then lexicographic, for determinism.
        return (-primary, len(str(path)), str(path))

    return sorted(members, key=sort_key)[0]


def plan_downloads_cleanup(
    organiser: FileOrganiserConfig,
    excluded_roots: list[Path],
    mode: str = "archive",
    older_than_days: int | None = None,
) -> FileActionResponse:
    """Plan archiving or trashing of downloads older than ``older_than_days``.

    ``archive`` moves files into the configured archive folder, preserving
    their path relative to the downloads directory; ``trash`` sends them to
    the XDG trash.
    """
    config = organiser.actions
    if mode not in DOWNLOAD_MODES:
        raise FileActionError(
            f"unknown mode {mode!r}; expected one of {', '.join(DOWNLOAD_MODES)}"
        )
    days = organiser.downloads_stale_days if older_than_days is None else older_than_days
    if days < 0:
        raise FileActionError("older_than_days must not be negative")

    root = Path(organiser.scan_root).expanduser().resolve()
    roots = [root]
    response = _new_response("clean_downloads", root, dry_run=True)

    downloads = Path(config.downloads_dir).expanduser()
    if not downloads.is_absolute():
        downloads = root / downloads
    try:
        downloads = resolve_within(downloads, roots)
    except PathEscapeError:
        raise FileActionError(
            "configured downloads_dir resolves outside the scan root"
        ) from None
    # Validate the archive destination before the early return below, so a
    # misconfiguration is reported even when there is nothing to move.
    archive_dir: Path | None = None
    if mode == "archive":
        candidate = Path(config.archive_dir).expanduser()
        if not candidate.is_absolute():
            candidate = root / candidate
        try:
            archive_dir = resolve_within(candidate, roots)
        except PathEscapeError:
            raise FileActionError(
                "configured archive_dir resolves outside the scan root"
            ) from None
        if archive_dir == downloads or downloads in archive_dir.parents:
            raise FileActionError(
                "archive_dir must not live inside the downloads directory"
            )

    if not downloads.is_dir():
        response.message = f"downloads directory {downloads} does not exist"
        return _finalise(response)

    cutoff = (datetime.now() - timedelta(days=days)).timestamp()
    response.message = f"downloads not modified in {days} day(s)"

    for path in walk_files(downloads, set(organiser.skip_dirs), excluded_roots):
        if len(response.operations) >= config.max_operations:
            response.truncated = True
            break
        try:
            mtime = path.lstat().st_mtime
        except OSError:
            continue
        if mtime > cutoff:
            continue

        age_days = int((datetime.now().timestamp() - mtime) // 86400)
        if mode == "trash":
            response.operations.append(FileOperation(
                action="trash",
                source=str(path),
                size_bytes=_size_of(path),
                reason=f"{age_days} days old",
            ))
            continue

        assert archive_dir is not None  # mode == "archive"
        destination = archive_dir / path.relative_to(downloads)
        operation = FileOperation(
            action="move",
            source=str(path),
            destination=str(destination),
            size_bytes=_size_of(path),
            reason=f"{age_days} days old",
        )
        if destination.exists() or destination.is_symlink():
            operation.status = "skipped"
            operation.reason = "destination already exists — not overwriting"
        response.operations.append(operation)

    return _finalise(response)


# ── Execution ────────────────────────────────────────────────────────


def execute_plan(
    response: FileActionResponse,
    organiser: FileOrganiserConfig,
    force_delete: bool = False,
    home: Path | None = None,
) -> FileActionResponse:
    """Carry out a planned manifest in place, recording per-operation status.

    Re-validates every path immediately before touching it: the plan was
    built from an earlier walk and the filesystem may have moved on.  An
    operation that no longer passes its safety checks becomes ``skipped``
    rather than failing the whole request.
    """
    config = organiser.actions
    root = Path(organiser.scan_root).expanduser().resolve()
    roots = [root]
    home = (home or root).expanduser().resolve()
    trash_root = trash_root_for(home, config.trash_dir)
    permanent_allowed = force_delete and config.allow_permanent_delete

    # Guard the duplicate invariant a second time, against the manifest
    # that is actually about to run.
    _assert_duplicates_retain_one(response)

    for operation in response.operations:
        if operation.status != "planned":
            continue
        try:
            source = resolve_within(operation.source, roots)
        except PathEscapeError as exc:
            operation.status = "skipped"
            operation.reason = str(exc)
            continue

        original = Path(operation.source)
        if original.is_symlink():
            operation.status = "skipped"
            operation.reason = "source is a symlink — never followed"
            continue
        if not source.is_file():
            operation.status = "skipped"
            operation.reason = "source no longer exists"
            continue

        try:
            if operation.action == "move":
                _execute_move(operation, source, roots)
            elif operation.action == "trash":
                _execute_trash(
                    operation, source, trash_root, permanent_allowed
                )
            else:
                operation.status = "skipped"
                operation.reason = f"unsupported action {operation.action!r}"
        except OSError as exc:
            operation.status = "failed"
            operation.reason = f"{type(exc).__name__}: {exc}"
            logger.warning(
                "file_action_failed",
                extra={
                    "action": operation.action,
                    "source": operation.source,
                    "error": str(exc),
                },
            )

    response.dry_run = False
    return _finalise(response)


def _execute_move(operation: FileOperation, source: Path, roots: list[Path]) -> None:
    if not operation.destination:
        operation.status = "skipped"
        operation.reason = "no destination"
        return
    try:
        destination = resolve_within(operation.destination, roots)
    except PathEscapeError as exc:
        operation.status = "skipped"
        operation.reason = str(exc)
        return
    if destination.exists() or destination.is_symlink():
        operation.status = "skipped"
        operation.reason = "destination already exists — not overwriting"
        return
    try:
        _safe_move(source, destination)
    except FileExistsError:
        operation.status = "skipped"
        operation.reason = "destination appeared during the move — not overwriting"
        return
    operation.destination = str(destination)
    operation.status = "done"


def _execute_trash(
    operation: FileOperation,
    source: Path,
    trash_root: Path,
    permanent_allowed: bool,
) -> None:
    if trash_is_usable(source, trash_root):
        operation.destination = str(send_to_trash(source, trash_root))
        operation.status = "done"
        return
    if not permanent_allowed:
        operation.status = "skipped"
        operation.reason = (
            "trash unavailable for this file (different filesystem); refusing "
            "an unrecoverable delete — set force_delete and enable "
            "actions.allow_permanent_delete to override"
        )
        return
    os.unlink(source)
    operation.action = "delete"
    operation.destination = None
    operation.status = "done"
    operation.reason = "permanently deleted (trash unavailable, delete forced)"


def _assert_duplicates_retain_one(response: FileActionResponse) -> None:
    """Fail loudly if a manifest would remove every copy of a duplicate group.

    ``keep_path`` is only set by the duplicate planner.  For every retained
    path in the manifest, that path must not itself be scheduled for
    removal — otherwise a group could be wiped out entirely.
    """
    removing = {
        o.source for o in response.operations
        if o.action in ("trash", "delete") and o.status == "planned"
    }
    for operation in response.operations:
        if operation.keep_path and operation.keep_path in removing:
            raise RuntimeError(
                f"refusing to run: retained copy {operation.keep_path} is also "
                "scheduled for removal"
            )
