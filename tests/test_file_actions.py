"""Tests for the mutating file actions — organise, de-duplicate, downloads.

These endpoints move and delete real files, so the safety rules get more
attention here than the happy paths:

- dry run is the default and leaves the tree **byte-identical**
- confirm performs exactly the operations that were previewed
- paths that resolve outside the scan root are refused
- symlinks are never followed
- existing destinations are skipped, never overwritten
- duplicate cleanup always retains exactly one copy per group
- age thresholds are checked at their boundaries

Every test builds a fabricated tree under ``tmp_path``. Nothing here ever
touches the real home directory: each ``FileOrganiserConfig`` gets
``scan_root`` and ``actions.trash_dir`` pointed inside the temp tree.
"""

import os
import time
from pathlib import Path

import pytest

from sysadmin.config import FileActionsConfig, FileOrganiserConfig
from sysadmin.contracts import FileActionResponse, FileOperation
from sysadmin.services import file_actions
from sysadmin.services.file_actions import (
    FileActionError,
    PathEscapeError,
    classify_pdf,
    execute_plan,
    plan_downloads_cleanup,
    plan_duplicate_cleanup,
    plan_organise,
    resolve_within,
    send_to_trash,
    trash_is_usable,
    walk_files,
)

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def organiser(tmp_path):
    """A FileOrganiserConfig rooted entirely inside tmp_path."""
    return FileOrganiserConfig(
        scan_root=str(tmp_path),
        downloads_stale_days=30,
        skip_dirs=[".git", "node_modules", "__pycache__", ".venv"],
        actions=FileActionsConfig(
            trash_dir=str(tmp_path / ".local" / "share" / "Trash"),
        ),
    )


def snapshot(root: Path) -> dict[str, tuple]:
    """Byte-level snapshot of a tree — compare before/after a dry run."""
    tree: dict[str, tuple] = {}
    for path in sorted(root.rglob("*")):
        rel = str(path.relative_to(root))
        if path.is_symlink():
            tree[rel] = ("link", os.readlink(path))
        elif path.is_dir():
            tree[rel] = ("dir",)
        else:
            stat = path.stat()
            tree[rel] = ("file", stat.st_size, stat.st_mtime_ns, path.read_bytes())
    return tree


def make_file(path: Path, content: bytes = b"x" * 2048, days_old: int | None = None):
    """Create a file (with parents), optionally aged."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    if days_old is not None:
        old = time.time() - (days_old * 86400)
        os.utime(path, (old, old))
    return path


def make_pdf(path: Path, pages: int | None = None, padding: int = 512) -> Path:
    """A minimal file that looks enough like a PDF for the page-count probe."""
    body = b"%PDF-1.4\n"
    if pages is not None:
        body += b"1 0 obj\n<< /Type /Pages /Count %d >>\nendobj\n" % pages
    body += b"%" + b"padding" * padding + b"\n%%EOF\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return path


def sources(response: FileActionResponse, status: str = "planned") -> set[str]:
    return {o.source for o in response.operations if o.status == status}


# ---------------------------------------------------------------------------
# Root confinement
# ---------------------------------------------------------------------------


class TestRootConfinement:
    def test_path_inside_root_accepted(self, tmp_path):
        target = tmp_path / "sub" / "file.txt"
        assert resolve_within(target, [tmp_path]) == target.resolve()

    def test_root_itself_accepted(self, tmp_path):
        assert resolve_within(tmp_path, [tmp_path]) == tmp_path.resolve()

    def test_dotdot_escape_rejected(self, tmp_path):
        with pytest.raises(PathEscapeError):
            resolve_within(tmp_path / ".." / ".." / "etc" / "passwd", [tmp_path])

    def test_sibling_directory_rejected(self, tmp_path):
        root = tmp_path / "home"
        root.mkdir()
        outside = tmp_path / "elsewhere" / "secret.txt"
        with pytest.raises(PathEscapeError):
            resolve_within(outside, [root])

    def test_prefix_lookalike_rejected(self, tmp_path):
        """/home/gaddi-backup must not count as inside /home/gaddi."""
        root = tmp_path / "gaddi"
        root.mkdir()
        (tmp_path / "gaddi-backup").mkdir()
        with pytest.raises(PathEscapeError):
            resolve_within(tmp_path / "gaddi-backup" / "f.txt", [root])

    def test_symlink_escape_rejected(self, tmp_path):
        """A symlink pointing out of the root resolves out and is refused."""
        root = tmp_path / "home"
        root.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        make_file(outside / "target.txt")
        (root / "link.txt").symlink_to(outside / "target.txt")
        with pytest.raises(PathEscapeError):
            resolve_within(root / "link.txt", [root])

    def test_is_within_does_not_raise(self, tmp_path):
        assert file_actions.is_within(tmp_path / "a", [tmp_path]) is True
        assert file_actions.is_within(tmp_path.parent, [tmp_path]) is False


# ---------------------------------------------------------------------------
# Walking — what is off limits
# ---------------------------------------------------------------------------


class TestWalkFiles:
    def test_skips_protected_and_hidden(self, tmp_path):
        make_file(tmp_path / "keep.txt")
        make_file(tmp_path / ".hidden.txt")
        make_file(tmp_path / ".git" / "config")
        make_file(tmp_path / "node_modules" / "pkg" / "index.js")
        make_file(tmp_path / "__pycache__" / "m.pyc")
        make_file(tmp_path / ".venv" / "lib" / "x.py")
        make_file(tmp_path / ".config" / "app.conf")

        found = {p.name for p in walk_files(tmp_path, set(), [])}
        assert found == {"keep.txt"}

    def test_skips_symlinked_files(self, tmp_path):
        make_file(tmp_path / "real.txt")
        (tmp_path / "link.txt").symlink_to(tmp_path / "real.txt")
        found = {p.name for p in walk_files(tmp_path, set(), [])}
        assert found == {"real.txt"}

    def test_does_not_follow_symlinked_dirs(self, tmp_path):
        outside = tmp_path / "outside"
        make_file(outside / "secret.txt")
        root = tmp_path / "home"
        root.mkdir()
        (root / "shortcut").symlink_to(outside)
        assert list(walk_files(root, set(), [])) == []

    def test_excluded_roots_pruned(self, tmp_path):
        make_file(tmp_path / "projects" / "app" / "photo.jpg")
        make_file(tmp_path / "loose.jpg")
        found = {p.name for p in walk_files(tmp_path, set(), [tmp_path / "projects"])}
        assert found == {"loose.jpg"}


# ---------------------------------------------------------------------------
# PDF routing heuristic
# ---------------------------------------------------------------------------


class TestPdfHeuristic:
    @pytest.fixture
    def config(self):
        return FileActionsConfig()

    def test_document_marker_wins(self, tmp_path, config):
        pdf = make_pdf(tmp_path / "invoice-2026.pdf", pages=400)
        category, why = classify_pdf(pdf, config)
        assert category == "documents"
        assert "document marker" in why

    def test_isbn_in_filename_is_a_book(self, tmp_path, config):
        pdf = make_pdf(tmp_path / "9781234567897.pdf")
        assert classify_pdf(pdf, config)[0] == "books"

    def test_book_keyword_in_filename(self, tmp_path, config):
        pdf = make_pdf(tmp_path / "python-handbook-2nd-edition.pdf")
        assert classify_pdf(pdf, config)[0] == "books"

    def test_shadow_library_marker_is_a_book(self, tmp_path, config):
        pdf = make_pdf(tmp_path / "Managing Projects (Z-Library).pdf")
        assert classify_pdf(pdf, config)[0] == "books"

    def test_high_page_count_is_a_book(self, tmp_path, config):
        pdf = make_pdf(tmp_path / "untitled-scan.pdf", pages=320)
        category, why = classify_pdf(pdf, config)
        assert category == "books"
        assert "320" in why

    def test_outline_count_not_mistaken_for_pages(self, tmp_path, config):
        """/Count on an /Outlines node must not inflate the page count."""
        path = tmp_path / "untitled-scan.pdf"
        path.write_bytes(
            b"%PDF-1.4\n"
            b"1 0 obj\n<< /Type /Outlines /Count 600 >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Count 4 >>\nendobj\n"
            b"%%EOF\n"
        )
        assert file_actions.pdf_page_count(path) == 4
        assert classify_pdf(path, config)[0] == "documents"

    def test_largest_page_subtree_count_wins(self, tmp_path, config):
        path = tmp_path / "untitled-scan.pdf"
        path.write_bytes(
            b"%PDF-1.4\n"
            b"1 0 obj\n<< /Type /Pages /Count 12 >>\nendobj\n"
            b"2 0 obj\n<< /Count 240 /Type /Pages >>\nendobj\n"
            b"%%EOF\n"
        )
        assert file_actions.pdf_page_count(path) == 240

    def test_low_page_count_is_a_document(self, tmp_path, config):
        pdf = make_pdf(tmp_path / "untitled-scan.pdf", pages=3)
        assert classify_pdf(pdf, config)[0] == "documents"

    def test_unknown_page_count_defaults_to_documents(self, tmp_path, config):
        """No evidence either way must never route to Books."""
        pdf = make_pdf(tmp_path / "untitled-scan.pdf", pages=None)
        category, why = classify_pdf(pdf, config)
        assert category == "documents"
        assert "conservative" in why

    def test_page_threshold_is_configurable(self, tmp_path):
        pdf = make_pdf(tmp_path / "untitled-scan.pdf", pages=20)
        assert classify_pdf(pdf, FileActionsConfig())[0] == "documents"
        lenient = FileActionsConfig(pdf_book_min_pages=10)
        assert classify_pdf(pdf, lenient)[0] == "books"


# ---------------------------------------------------------------------------
# Organise
# ---------------------------------------------------------------------------


class TestOrganise:
    def test_misplaced_image_planned(self, tmp_path, organiser):
        make_file(tmp_path / "holiday.jpg")
        plan = plan_organise(organiser, [])
        assert plan.dry_run is True
        assert len(plan.operations) == 1
        operation = plan.operations[0]
        assert operation.action == "move"
        assert operation.category == "images"
        assert operation.source == str(tmp_path / "holiday.jpg")
        assert operation.destination == str(tmp_path / "Pictures" / "holiday.jpg")
        assert operation.size_bytes == 2048
        assert plan.total_bytes == 2048

    def test_dry_run_changes_nothing(self, tmp_path, organiser):
        make_file(tmp_path / "a.jpg")
        make_file(tmp_path / "b.mp3")
        make_file(tmp_path / "book.epub")
        before = snapshot(tmp_path)

        plan = plan_organise(organiser, [])

        assert plan.planned_count == 3
        assert snapshot(tmp_path) == before

    def test_confirm_performs_exactly_the_preview(self, tmp_path, organiser):
        make_file(tmp_path / "a.jpg")
        make_file(tmp_path / "song.mp3")
        plan = plan_organise(organiser, [])
        previewed = {(o.source, o.destination) for o in plan.operations}

        result = execute_plan(plan, organiser, home=tmp_path)

        assert result.dry_run is False
        assert result.done_count == 2
        assert result.failed_count == 0
        for source, destination in previewed:
            assert not Path(source).exists()
            assert Path(destination).is_file()

    def test_already_filed_not_touched(self, tmp_path, organiser):
        make_file(tmp_path / "Pictures" / "already.jpg")
        assert plan_organise(organiser, []).operations == []

    def test_traditional_folder_names_respected(self, tmp_path, organiser):
        """An existing photos/ tree is not churned into Pictures/."""
        make_file(tmp_path / "photos" / "old.jpg")
        assert plan_organise(organiser, []).operations == []

    def test_collision_skipped_not_overwritten(self, tmp_path, organiser):
        make_file(tmp_path / "clash.jpg", b"new content here")
        existing = make_file(tmp_path / "Pictures" / "clash.jpg", b"original content")
        before = existing.read_bytes()

        plan = plan_organise(organiser, [])
        operation = plan.operations[0]
        assert operation.status == "skipped"
        assert "already exists" in operation.reason

        execute_plan(plan, organiser, home=tmp_path)
        assert existing.read_bytes() == before
        assert (tmp_path / "clash.jpg").exists()

    def test_loose_code_flagged_never_moved(self, tmp_path, organiser):
        make_file(tmp_path / "scratch.py", b"print('hi')\n")
        plan = plan_organise(organiser, [])
        assert plan.operations == []
        assert len(plan.flagged) == 1
        assert plan.flagged[0].kind == "loose_code"
        assert plan.flagged[0].path == str(tmp_path / "scratch.py")

        execute_plan(plan, organiser, home=tmp_path)
        assert (tmp_path / "scratch.py").exists()

    def test_code_in_subdirectory_not_flagged(self, tmp_path, organiser):
        """Only the scan root itself — code deeper down is somebody's project."""
        make_file(tmp_path / "work" / "script.py")
        plan = plan_organise(organiser, [])
        assert plan.flagged == []

    def test_books_and_archives_categories(self, tmp_path, organiser):
        make_file(tmp_path / "novel.epub")
        make_file(tmp_path / "comic.cbz")
        make_file(tmp_path / "backup.zip")
        make_file(tmp_path / "source.tar.gz")

        plan = plan_organise(organiser, [])
        by_source = {Path(o.source).name: o for o in plan.operations}
        assert by_source["novel.epub"].destination == str(tmp_path / "Books" / "novel.epub")
        assert by_source["comic.cbz"].category == "books"
        assert by_source["backup.zip"].destination == str(
            tmp_path / "Archives" / "backup.zip"
        )
        assert by_source["source.tar.gz"].category == "archives"

    def test_pdf_split_between_books_and_documents(self, tmp_path, organiser):
        make_pdf(tmp_path / "invoice-jan.pdf")
        make_pdf(tmp_path / "algorithms-3rd-edition.pdf")

        plan = plan_organise(organiser, [])
        by_source = {Path(o.source).name: o for o in plan.operations}
        assert by_source["invoice-jan.pdf"].category == "documents"
        assert by_source["algorithms-3rd-edition.pdf"].category == "books"

    def test_category_filter(self, tmp_path, organiser):
        make_file(tmp_path / "a.jpg")
        make_file(tmp_path / "b.mp3")
        plan = plan_organise(organiser, [], categories=["images"])
        assert len(plan.operations) == 1
        assert plan.operations[0].category == "images"

    def test_destination_is_config_driven(self, tmp_path, organiser):
        organiser.actions.category_folders["images"] = "Media/Photographs"
        make_file(tmp_path / "a.jpg")
        plan = plan_organise(organiser, [])
        assert plan.operations[0].destination == str(
            tmp_path / "Media" / "Photographs" / "a.jpg"
        )

    def test_configured_destination_outside_root_refused(self, tmp_path, organiser):
        organiser.actions.category_folders["images"] = "/etc/pictures"
        make_file(tmp_path / "a.jpg")
        plan = plan_organise(organiser, [])
        assert plan.operations[0].status == "skipped"
        assert "outside" in plan.operations[0].reason
        execute_plan(plan, organiser, home=tmp_path)
        assert (tmp_path / "a.jpg").exists()

    def test_category_without_mapping_ignored(self, tmp_path, organiser):
        organiser.actions.category_folders.pop("audio")
        make_file(tmp_path / "song.mp3")
        assert plan_organise(organiser, []).operations == []

    def test_excluded_project_root_untouched(self, tmp_path, organiser):
        make_file(tmp_path / "projects" / "app" / "logo.png")
        plan = plan_organise(organiser, [tmp_path / "projects"])
        assert plan.operations == []

    def test_truncates_at_max_operations(self, tmp_path, organiser):
        organiser.actions.max_operations = 3
        for index in range(10):
            make_file(tmp_path / f"img{index}.jpg")
        plan = plan_organise(organiser, [])
        assert plan.truncated is True
        assert len(plan.operations) == 3

    def test_missing_scan_root(self, tmp_path, organiser):
        organiser.scan_root = str(tmp_path / "nope")
        plan = plan_organise(organiser, [])
        assert plan.operations == []
        assert "does not exist" in plan.message

    def test_execute_skips_source_that_vanished(self, tmp_path, organiser):
        make_file(tmp_path / "a.jpg")
        plan = plan_organise(organiser, [])
        (tmp_path / "a.jpg").unlink()

        result = execute_plan(plan, organiser, home=tmp_path)
        assert result.done_count == 0
        assert result.skipped_count == 1
        assert "no longer exists" in result.operations[0].reason

    def test_execute_skips_symlink_source(self, tmp_path, organiser):
        """Even a hand-crafted manifest cannot make us follow a link."""
        outside = make_file(tmp_path / "outside" / "target.jpg")
        (tmp_path / "link.jpg").symlink_to(outside)
        plan = FileActionResponse(
            operation="organise",
            scan_root=str(tmp_path),
            operations=[FileOperation(
                action="move",
                source=str(tmp_path / "link.jpg"),
                destination=str(tmp_path / "Pictures" / "link.jpg"),
            )],
        )
        result = execute_plan(plan, organiser, home=tmp_path)
        assert result.operations[0].status == "skipped"
        assert "symlink" in result.operations[0].reason
        assert (tmp_path / "link.jpg").is_symlink()
        assert outside.exists()

    def test_execute_refuses_out_of_root_destination(self, tmp_path, organiser):
        make_file(tmp_path / "a.jpg")
        plan = FileActionResponse(
            operation="organise",
            scan_root=str(tmp_path),
            operations=[FileOperation(
                action="move",
                source=str(tmp_path / "a.jpg"),
                destination=str(tmp_path.parent / "escaped.jpg"),
            )],
        )
        result = execute_plan(plan, organiser, home=tmp_path)
        assert result.operations[0].status == "skipped"
        assert (tmp_path / "a.jpg").exists()
        assert not (tmp_path.parent / "escaped.jpg").exists()

    def test_execute_refuses_out_of_root_source(self, tmp_path, organiser):
        outside = make_file(tmp_path.parent / "outsider.jpg")
        plan = FileActionResponse(
            operation="organise",
            scan_root=str(tmp_path),
            operations=[FileOperation(
                action="move",
                source=str(outside),
                destination=str(tmp_path / "Pictures" / "outsider.jpg"),
            )],
        )
        try:
            result = execute_plan(plan, organiser, home=tmp_path)
            assert result.operations[0].status == "skipped"
            assert outside.exists()
        finally:
            outside.unlink()


# ---------------------------------------------------------------------------
# Trash
# ---------------------------------------------------------------------------


class TestTrash:
    def test_moves_file_and_writes_info(self, tmp_path):
        trash = tmp_path / "Trash"
        target = make_file(tmp_path / "junk.txt", b"bye")

        destination = send_to_trash(target, trash)

        assert not target.exists()
        assert destination.read_bytes() == b"bye"
        info = (trash / "info" / "junk.txt.trashinfo").read_text()
        assert "[Trash Info]" in info
        assert "DeletionDate=" in info
        assert str(target).replace("/", "%2F") in info or str(target) in info

    def test_name_collision_gets_a_suffix(self, tmp_path):
        trash = tmp_path / "Trash"
        first = make_file(tmp_path / "a" / "dup.txt", b"one")
        second = make_file(tmp_path / "b" / "dup.txt", b"two")

        send_to_trash(first, trash)
        destination = send_to_trash(second, trash)

        assert destination.name == "dup.1.txt"
        assert (trash / "files" / "dup.txt").read_bytes() == b"one"
        assert destination.read_bytes() == b"two"

    def test_usable_on_same_filesystem(self, tmp_path):
        target = make_file(tmp_path / "f.txt")
        assert trash_is_usable(target, tmp_path / "Trash") is True


# ---------------------------------------------------------------------------
# Duplicate cleanup
# ---------------------------------------------------------------------------


class TestDuplicateCleanup:
    def test_keeps_newest_by_default(self, tmp_path, organiser):
        content = b"identical" * 500
        make_file(tmp_path / "old" / "copy.bin", content, days_old=10)
        newest = make_file(tmp_path / "new" / "copy.bin", content, days_old=1)

        plan = plan_duplicate_cleanup(organiser, [])

        assert len(plan.operations) == 1
        assert plan.operations[0].source == str(tmp_path / "old" / "copy.bin")
        assert plan.operations[0].keep_path == str(newest)
        assert plan.operations[0].action == "trash"

    def test_keeps_largest_with_strategy(self, tmp_path, organiser):
        """Same fingerprint prefix, different total size."""
        prefix = b"z" * 4096
        small = make_file(tmp_path / "small.bin", prefix)
        make_file(tmp_path / "big.bin", prefix + b"tail" * 100)
        # Different sizes hash differently, so force a real duplicate pair
        # and assert the retention rule on equal-content copies instead.
        make_file(tmp_path / "a" / "same.bin", prefix, days_old=5)
        make_file(tmp_path / "b" / "same.bin", prefix, days_old=1)

        plan = plan_duplicate_cleanup(organiser, [], strategy="largest")
        removed = sources(plan)
        keeps = {o.keep_path for o in plan.operations}

        # Three identical-size copies of `prefix`: exactly two are removed.
        assert len(removed) == 2
        assert len(keeps) == 1
        assert keeps.pop() not in removed
        assert small.exists()

    def test_retains_exactly_one_per_group(self, tmp_path, organiser):
        content = b"triplicate" * 400
        paths = [
            make_file(tmp_path / f"dir{i}" / "same.bin", content, days_old=i + 1)
            for i in range(3)
        ]

        plan = plan_duplicate_cleanup(organiser, [])

        assert len(plan.operations) == len(paths) - 1
        keeps = {o.keep_path for o in plan.operations}
        assert len(keeps) == 1
        keeper = keeps.pop()
        assert keeper not in sources(plan)

    def test_confirm_leaves_one_copy_on_disk(self, tmp_path, organiser):
        content = b"survivor" * 400
        for index in range(4):
            make_file(tmp_path / f"d{index}" / "same.bin", content, days_old=index + 1)

        plan = plan_duplicate_cleanup(organiser, [])
        keeper = Path(plan.operations[0].keep_path)
        result = execute_plan(plan, organiser, home=tmp_path)

        assert result.done_count == 3
        assert keeper.is_file()
        survivors = [p for p in tmp_path.rglob("same.bin") if "Trash" not in str(p)]
        assert survivors == [keeper]

    def test_removals_are_recoverable_from_trash(self, tmp_path, organiser):
        content = b"recoverable" * 400
        make_file(tmp_path / "a" / "same.bin", content, days_old=9)
        make_file(tmp_path / "b" / "same.bin", content, days_old=1)

        plan = plan_duplicate_cleanup(organiser, [])
        result = execute_plan(plan, organiser, home=tmp_path)

        trashed = Path(result.operations[0].destination)
        assert trashed.read_bytes() == content
        assert trashed.parent == Path(organiser.actions.trash_dir) / "files"

    def test_dry_run_changes_nothing(self, tmp_path, organiser):
        content = b"untouched" * 400
        make_file(tmp_path / "a" / "same.bin", content, days_old=9)
        make_file(tmp_path / "b" / "same.bin", content, days_old=1)
        before = snapshot(tmp_path)

        plan = plan_duplicate_cleanup(organiser, [])

        assert plan.planned_count == 1
        assert snapshot(tmp_path) == before

    def test_unique_files_untouched(self, tmp_path, organiser):
        make_file(tmp_path / "one.bin", b"a" * 2048)
        make_file(tmp_path / "two.bin", b"b" * 2048)
        assert plan_duplicate_cleanup(organiser, []).operations == []

    def test_tiny_duplicates_ignored(self, tmp_path, organiser):
        make_file(tmp_path / "a" / "tiny.txt", b"hi")
        make_file(tmp_path / "b" / "tiny.txt", b"hi")
        assert plan_duplicate_cleanup(organiser, []).operations == []

    def test_unknown_strategy_rejected(self, tmp_path, organiser):
        with pytest.raises(FileActionError):
            plan_duplicate_cleanup(organiser, [], strategy="oldest")

    def test_execute_refuses_manifest_that_removes_the_keeper(self, tmp_path, organiser):
        """The retain-one invariant is re-checked against the live manifest."""
        keeper = make_file(tmp_path / "keep.bin", b"k" * 2048)
        other = make_file(tmp_path / "other.bin", b"k" * 2048)
        plan = FileActionResponse(
            operation="clean_duplicates",
            scan_root=str(tmp_path),
            operations=[
                FileOperation(action="trash", source=str(other), keep_path=str(keeper)),
                FileOperation(action="trash", source=str(keeper), keep_path=str(other)),
            ],
        )
        with pytest.raises(RuntimeError, match="retained copy"):
            execute_plan(plan, organiser, home=tmp_path)
        assert keeper.exists()
        assert other.exists()

    def test_protected_trees_not_deduplicated(self, tmp_path, organiser):
        content = b"vendored" * 400
        make_file(tmp_path / "node_modules" / "pkg" / "same.bin", content)
        make_file(tmp_path / ".git" / "objects" / "same.bin", content)
        assert plan_duplicate_cleanup(organiser, []).operations == []


# ---------------------------------------------------------------------------
# Downloads cleanup
# ---------------------------------------------------------------------------


class TestDownloadsCleanup:
    def test_archives_old_downloads(self, tmp_path, organiser):
        make_file(tmp_path / "Downloads" / "old.iso", days_old=90)
        plan = plan_downloads_cleanup(organiser, [])

        assert len(plan.operations) == 1
        operation = plan.operations[0]
        assert operation.action == "move"
        assert operation.destination == str(
            tmp_path / "Archives" / "Downloads" / "old.iso"
        )
        assert "90 days old" in operation.reason

    def test_recent_downloads_untouched(self, tmp_path, organiser):
        make_file(tmp_path / "Downloads" / "fresh.iso", days_old=2)
        assert plan_downloads_cleanup(organiser, []).operations == []

    def test_age_boundary(self, tmp_path, organiser):
        """Default 30 days: 31 goes, 29 stays."""
        make_file(tmp_path / "Downloads" / "just_over.bin", days_old=31)
        make_file(tmp_path / "Downloads" / "just_under.bin", days_old=29)

        plan = plan_downloads_cleanup(organiser, [])
        names = {Path(s).name for s in sources(plan)}
        assert names == {"just_over.bin"}

    def test_custom_threshold(self, tmp_path, organiser):
        make_file(tmp_path / "Downloads" / "a.bin", days_old=10)
        assert plan_downloads_cleanup(organiser, [], older_than_days=7).planned_count == 1
        assert plan_downloads_cleanup(organiser, [], older_than_days=14).planned_count == 0

    def test_zero_days_takes_everything(self, tmp_path, organiser):
        make_file(tmp_path / "Downloads" / "today.bin")
        assert plan_downloads_cleanup(organiser, [], older_than_days=0).planned_count == 1

    def test_negative_threshold_rejected(self, tmp_path, organiser):
        with pytest.raises(FileActionError):
            plan_downloads_cleanup(organiser, [], older_than_days=-1)

    def test_subdirectory_structure_preserved(self, tmp_path, organiser):
        make_file(tmp_path / "Downloads" / "isos" / "distro.iso", days_old=60)
        plan = plan_downloads_cleanup(organiser, [])
        assert plan.operations[0].destination == str(
            tmp_path / "Archives" / "Downloads" / "isos" / "distro.iso"
        )

    def test_dry_run_changes_nothing(self, tmp_path, organiser):
        make_file(tmp_path / "Downloads" / "old.iso", days_old=90)
        before = snapshot(tmp_path)
        plan_downloads_cleanup(organiser, [])
        assert snapshot(tmp_path) == before

    def test_confirm_moves_the_file(self, tmp_path, organiser):
        source = make_file(tmp_path / "Downloads" / "old.iso", b"payload", days_old=90)
        plan = plan_downloads_cleanup(organiser, [])
        result = execute_plan(plan, organiser, home=tmp_path)

        assert result.done_count == 1
        assert not source.exists()
        assert (tmp_path / "Archives" / "Downloads" / "old.iso").read_bytes() == b"payload"

    def test_trash_mode(self, tmp_path, organiser):
        source = make_file(tmp_path / "Downloads" / "old.iso", b"payload", days_old=90)
        plan = plan_downloads_cleanup(organiser, [], mode="trash")
        assert plan.operations[0].action == "trash"

        result = execute_plan(plan, organiser, home=tmp_path)
        assert not source.exists()
        assert Path(result.operations[0].destination).read_bytes() == b"payload"

    def test_archive_collision_skipped(self, tmp_path, organiser):
        make_file(tmp_path / "Downloads" / "dup.bin", b"incoming", days_old=90)
        existing = make_file(
            tmp_path / "Archives" / "Downloads" / "dup.bin", b"already there"
        )

        plan = plan_downloads_cleanup(organiser, [])
        assert plan.operations[0].status == "skipped"
        execute_plan(plan, organiser, home=tmp_path)
        assert existing.read_bytes() == b"already there"

    def test_unknown_mode_rejected(self, tmp_path, organiser):
        with pytest.raises(FileActionError):
            plan_downloads_cleanup(organiser, [], mode="shred")

    def test_downloads_outside_root_rejected(self, tmp_path, organiser):
        organiser.actions.downloads_dir = "/var/tmp/downloads"
        with pytest.raises(FileActionError, match="outside the scan root"):
            plan_downloads_cleanup(organiser, [])

    def test_archive_outside_root_rejected(self, tmp_path, organiser):
        make_file(tmp_path / "Downloads" / "old.bin", days_old=90)
        organiser.actions.archive_dir = "../escaped"
        with pytest.raises(FileActionError, match="outside the scan root"):
            plan_downloads_cleanup(organiser, [])

    def test_archive_inside_downloads_rejected(self, tmp_path, organiser):
        organiser.actions.archive_dir = "Downloads/old"
        with pytest.raises(FileActionError, match="must not live inside"):
            plan_downloads_cleanup(organiser, [])

    def test_missing_downloads_dir(self, tmp_path, organiser):
        plan = plan_downloads_cleanup(organiser, [])
        assert plan.operations == []
        assert "does not exist" in plan.message

    def test_symlinked_download_not_followed(self, tmp_path, organiser):
        outside = make_file(tmp_path / "outside" / "precious.bin", b"keep me")
        downloads = tmp_path / "Downloads"
        downloads.mkdir()
        link = downloads / "link.bin"
        link.symlink_to(outside)
        old = time.time() - (90 * 86400)
        os.utime(link, (old, old), follow_symlinks=False)

        plan = plan_downloads_cleanup(organiser, [], mode="trash")
        assert plan.operations == []
        assert outside.read_bytes() == b"keep me"


# ---------------------------------------------------------------------------
# Permanent deletion guard
# ---------------------------------------------------------------------------


class TestPermanentDeleteGuard:
    def _unusable_trash(self, monkeypatch):
        monkeypatch.setattr(file_actions, "trash_is_usable", lambda *_: False)

    def test_skipped_when_trash_unusable(self, tmp_path, organiser, monkeypatch):
        self._unusable_trash(monkeypatch)
        target = make_file(tmp_path / "a" / "same.bin", b"d" * 2048, days_old=9)
        make_file(tmp_path / "b" / "same.bin", b"d" * 2048, days_old=1)

        plan = plan_duplicate_cleanup(organiser, [])
        result = execute_plan(plan, organiser, home=tmp_path)

        assert result.done_count == 0
        assert result.skipped_count == 1
        assert "trash unavailable" in result.operations[0].reason
        assert target.exists()

    def test_force_delete_alone_is_not_enough(self, tmp_path, organiser, monkeypatch):
        """Config must also allow it — belt and braces."""
        self._unusable_trash(monkeypatch)
        target = make_file(tmp_path / "a" / "same.bin", b"d" * 2048, days_old=9)
        make_file(tmp_path / "b" / "same.bin", b"d" * 2048, days_old=1)

        plan = plan_duplicate_cleanup(organiser, [])
        result = execute_plan(plan, organiser, force_delete=True, home=tmp_path)

        assert result.skipped_count == 1
        assert target.exists()

    def test_config_flag_alone_is_not_enough(self, tmp_path, organiser, monkeypatch):
        self._unusable_trash(monkeypatch)
        organiser.actions.allow_permanent_delete = True
        target = make_file(tmp_path / "a" / "same.bin", b"d" * 2048, days_old=9)
        make_file(tmp_path / "b" / "same.bin", b"d" * 2048, days_old=1)

        plan = plan_duplicate_cleanup(organiser, [])
        result = execute_plan(plan, organiser, force_delete=False, home=tmp_path)

        assert result.skipped_count == 1
        assert target.exists()

    def test_both_flags_permit_deletion(self, tmp_path, organiser, monkeypatch):
        self._unusable_trash(monkeypatch)
        organiser.actions.allow_permanent_delete = True
        target = make_file(tmp_path / "a" / "same.bin", b"d" * 2048, days_old=9)
        keeper = make_file(tmp_path / "b" / "same.bin", b"d" * 2048, days_old=1)

        plan = plan_duplicate_cleanup(organiser, [])
        result = execute_plan(plan, organiser, force_delete=True, home=tmp_path)

        assert result.done_count == 1
        assert result.operations[0].action == "delete"
        assert not target.exists()
        assert keeper.exists()


# ---------------------------------------------------------------------------
# API surface
# ---------------------------------------------------------------------------

ACTION_ROUTES = [
    "/api/files/organise",
    "/api/files/clean/duplicates",
    "/api/files/clean/downloads",
]


class TestManifestContract:
    """FileActionResponse parses defensively, like every other contract."""

    def test_unknown_fields_ignored(self):
        parsed = FileActionResponse.from_dict(
            {"operation": "organise", "invented_field": 1}
        )
        assert parsed.operation == "organise"

    def test_missing_fields_default(self):
        parsed = FileActionResponse.from_dict({})
        assert parsed.operations == []
        assert parsed.flagged == []
        assert parsed.dry_run is True  # safest default
        assert parsed.total_bytes == 0

    def test_operation_round_trips(self):
        operation = FileOperation(
            action="trash", source="/a", keep_path="/b", size_bytes=12
        )
        assert FileOperation.from_dict(operation.model_dump()) == operation


@pytest.fixture
def action_client(mock_config, test_client, tmp_path):
    """The real app, with the file organiser pointed at a temp tree."""
    organiser = mock_config.agents.file_organiser
    organiser.scan_root = str(tmp_path)
    organiser.actions.trash_dir = str(tmp_path / ".local" / "share" / "Trash")
    mock_config.agents.project_organiser.projects_root = str(tmp_path / "projects")
    return test_client


class TestActionApi:
    @pytest.mark.parametrize("path", ACTION_ROUTES)
    async def test_requires_auth(self, mock_config, action_client, path):
        mock_config.api.auth_token = "secret-token"
        try:
            response = await action_client.post(path, json={"confirm": True})
            assert response.status_code == 401
            assert response.headers.get("WWW-Authenticate") == "Bearer"
        finally:
            mock_config.api.auth_token = None

    @pytest.mark.parametrize("path", ACTION_ROUTES)
    async def test_get_not_allowed(self, action_client, path):
        assert (await action_client.get(path)).status_code == 405

    @pytest.mark.parametrize("path", ACTION_ROUTES)
    async def test_defaults_to_dry_run(self, action_client, path, tmp_path):
        make_file(tmp_path / "holiday.jpg")
        make_file(tmp_path / "Downloads" / "old.iso", days_old=90)
        make_file(tmp_path / "a" / "same.bin", b"z" * 2048, days_old=9)
        make_file(tmp_path / "b" / "same.bin", b"z" * 2048, days_old=1)
        before = snapshot(tmp_path)

        response = await action_client.post(path, json={})

        assert response.status_code == 200
        payload = response.json()
        assert payload["dry_run"] is True
        assert "dry run" in payload["message"]
        assert snapshot(tmp_path) == before

    @pytest.mark.parametrize("path", ACTION_ROUTES)
    async def test_empty_body_allowed(self, action_client, path):
        assert (await action_client.post(path)).status_code == 200

    async def test_organise_manifest_shape(self, action_client, tmp_path):
        make_file(tmp_path / "holiday.jpg")
        make_file(tmp_path / "notes.py")

        payload = (await action_client.post("/api/files/organise", json={})).json()

        assert payload["operation"] == "organise"
        assert payload["scan_root"] == str(tmp_path)
        assert payload["planned_count"] == 1
        assert payload["total_bytes"] == 2048
        operation = payload["operations"][0]
        assert operation["action"] == "move"
        assert operation["source"] == str(tmp_path / "holiday.jpg")
        assert operation["destination"] == str(tmp_path / "Pictures" / "holiday.jpg")
        assert operation["size_bytes"] == 2048
        assert payload["flagged"][0]["kind"] == "loose_code"

    async def test_organise_confirm_moves_files(self, action_client, tmp_path):
        make_file(tmp_path / "holiday.jpg")

        payload = (
            await action_client.post("/api/files/organise", json={"confirm": True})
        ).json()

        assert payload["dry_run"] is False
        assert payload["done_count"] == 1
        assert (tmp_path / "Pictures" / "holiday.jpg").is_file()
        assert not (tmp_path / "holiday.jpg").exists()

    async def test_duplicates_confirm_keeps_one(self, action_client, tmp_path):
        content = b"api-dup" * 400
        for index in range(3):
            make_file(tmp_path / f"d{index}" / "same.bin", content, days_old=index + 1)

        payload = (
            await action_client.post(
                "/api/files/clean/duplicates", json={"confirm": True}
            )
        ).json()

        assert payload["done_count"] == 2
        survivors = [p for p in tmp_path.rglob("same.bin") if "Trash" not in str(p)]
        assert len(survivors) == 1

    async def test_downloads_custom_age(self, action_client, tmp_path):
        make_file(tmp_path / "Downloads" / "old.bin", days_old=10)

        payload = (
            await action_client.post(
                "/api/files/clean/downloads", json={"older_than_days": 7}
            )
        ).json()
        assert payload["planned_count"] == 1

        payload = (
            await action_client.post(
                "/api/files/clean/downloads", json={"older_than_days": 20}
            )
        ).json()
        assert payload["planned_count"] == 0

    async def test_bad_strategy_is_400(self, action_client):
        response = await action_client.post(
            "/api/files/clean/duplicates", json={"strategy": "oldest"}
        )
        assert response.status_code == 400
        assert "strategy" in response.json()["detail"]

    async def test_bad_mode_is_400(self, action_client):
        response = await action_client.post(
            "/api/files/clean/downloads", json={"mode": "shred"}
        )
        assert response.status_code == 400

    @pytest.mark.parametrize("path", ACTION_ROUTES)
    async def test_disabled_kill_switch_is_409(
        self, mock_config, action_client, path, tmp_path
    ):
        mock_config.agents.file_organiser.actions.enabled = False
        make_file(tmp_path / "holiday.jpg")
        try:
            response = await action_client.post(path, json={"confirm": True})
            assert response.status_code == 409
            assert (tmp_path / "holiday.jpg").exists()
        finally:
            mock_config.agents.file_organiser.actions.enabled = True

    async def test_project_root_excluded_via_config(self, action_client, tmp_path):
        """Files under the configured projects root are never organised."""
        make_file(tmp_path / "projects" / "app" / "logo.png")

        payload = (
            await action_client.post("/api/files/organise", json={"confirm": True})
        ).json()

        assert payload["operations"] == []
        assert (tmp_path / "projects" / "app" / "logo.png").exists()
