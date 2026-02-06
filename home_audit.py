#!/usr/bin/env python3

import os
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from difflib import SequenceMatcher
import re

CONFIG = {
    "scan_root": Path.home(),
    "output_dir": Path.home() / "Documents/DMDocs/Self/Briefings/Audits",
    "stale_days": 180,
    "downloads_stale_days": 30,
    "large_file_mb": 100,
    "hash_chunk_size": 1024 * 1024,
    "similarity_threshold": 0.75,
    "skip_hidden": True,
    "skip_dirs": {".git", ".cache", ".local", ".config", ".var", ".mozilla", ".steam"},
}

FILE_CATEGORIES = {
    "images": {
        "extensions": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".svg", ".ico", ".heic", ".raw"},
        "expected_dirs": {"Pictures", "Images", "photos", "screenshots"},
    },
    "videos": {
        "extensions": {".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".wmv", ".m4v"},
        "expected_dirs": {"Videos", "Movies"},
    },
    "documents": {
        "extensions": {".pdf", ".docx", ".doc", ".odt", ".xlsx", ".xls", ".pptx", ".ppt", ".txt", ".rtf", ".epub"},
        "expected_dirs": {"Documents", "Docs"},
    },
    "audio": {
        "extensions": {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".wma"},
        "expected_dirs": {"Music", "Audio"},
    },
}

STALE_PROJECT_DIRS = {"node_modules", "__pycache__", ".venv", "venv", "target", "build", "dist", ".tox", ".pytest_cache"}


class HomeAuditor:
    def __init__(self):
        self.scan_root = CONFIG["scan_root"]
        self.now = datetime.now()
        self.stale_cutoff = self.now - timedelta(days=CONFIG["stale_days"])
        self.downloads_cutoff = self.now - timedelta(days=CONFIG["downloads_stale_days"])
        self.large_threshold = CONFIG["large_file_mb"] * 1024 * 1024

        self.similar_folders = []
        self.misplaced_files = defaultdict(list)
        self.stale_files = []
        self.old_downloads = []
        self.large_files = []
        self.duplicates = []
        self.empty_dirs = []
        self.stale_project_dirs = []

        self.all_dirs = []
        self.file_hashes = defaultdict(list)

    def should_skip(self, path: Path) -> bool:
        if CONFIG["skip_hidden"] and path.name.startswith("."):
            return True
        if path.name in CONFIG["skip_dirs"]:
            return True
        return False

    def get_file_hash(self, filepath: Path) -> str | None:
        try:
            hasher = hashlib.md5()
            size = filepath.stat().st_size
            hasher.update(str(size).encode())
            with open(filepath, "rb") as f:
                chunk = f.read(CONFIG["hash_chunk_size"])
                hasher.update(chunk)
            return hasher.hexdigest()
        except (PermissionError, OSError):
            return None

    def get_mtime(self, path: Path) -> datetime | None:
        try:
            return datetime.fromtimestamp(path.stat().st_mtime)
        except (PermissionError, OSError):
            return None

    def get_size(self, path: Path) -> int:
        try:
            return path.stat().st_size
        except (PermissionError, OSError):
            return 0

    def normalise_name(self, name: str) -> str:
        return re.sub(r"[\s_-]+", "", name.lower())

    def find_similar_folders(self):
        normalised = defaultdict(list)
        for d in self.all_dirs:
            norm = self.normalise_name(d.name)
            normalised[norm].append(d)

        for norm, dirs in normalised.items():
            if len(dirs) > 1:
                self.similar_folders.append(dirs)

        seen_pairs = set()
        for i, dir1 in enumerate(self.all_dirs):
            for dir2 in self.all_dirs[i + 1 :]:
                if dir1.parent == dir2.parent:
                    continue
                norm1, norm2 = self.normalise_name(dir1.name), self.normalise_name(dir2.name)
                if norm1 == norm2:
                    continue
                ratio = SequenceMatcher(None, norm1, norm2).ratio()
                if ratio >= CONFIG["similarity_threshold"]:
                    pair = tuple(sorted([str(dir1), str(dir2)]))
                    if pair not in seen_pairs:
                        seen_pairs.add(pair)
                        self.similar_folders.append([dir1, dir2])

    def check_misplaced(self, filepath: Path):
        ext = filepath.suffix.lower()
        rel_parts = filepath.relative_to(self.scan_root).parts

        for category, config in FILE_CATEGORIES.items():
            if ext in config["extensions"]:
                in_expected = any(part in config["expected_dirs"] for part in rel_parts)
                if not in_expected:
                    self.misplaced_files[category].append(filepath)
                break

    def check_stale(self, filepath: Path):
        mtime = self.get_mtime(filepath)
        if mtime and mtime < self.stale_cutoff:
            self.stale_files.append((filepath, mtime))

    def check_downloads(self, filepath: Path):
        rel = filepath.relative_to(self.scan_root)
        if rel.parts and rel.parts[0].lower() == "downloads":
            mtime = self.get_mtime(filepath)
            if mtime and mtime < self.downloads_cutoff:
                self.old_downloads.append((filepath, mtime))

    def check_large(self, filepath: Path):
        size = self.get_size(filepath)
        if size >= self.large_threshold:
            self.large_files.append((filepath, size))

    def check_duplicate(self, filepath: Path):
        size = self.get_size(filepath)
        if size < 1024:
            return
        file_hash = self.get_file_hash(filepath)
        if file_hash:
            self.file_hashes[file_hash].append(filepath)

    def check_empty_dir(self, dirpath: Path):
        try:
            if not any(dirpath.iterdir()):
                self.empty_dirs.append(dirpath)
        except PermissionError:
            pass

    def check_stale_project_dir(self, dirpath: Path):
        if dirpath.name in STALE_PROJECT_DIRS:
            size = sum(f.stat().st_size for f in dirpath.rglob("*") if f.is_file())
            self.stale_project_dirs.append((dirpath, size))

    def scan(self):
        print(f"Scanning {self.scan_root}...")

        for root, dirs, files in os.walk(self.scan_root):
            root_path = Path(root)

            dirs[:] = [d for d in dirs if not self.should_skip(root_path / d)]

            for d in dirs:
                dirpath = root_path / d
                self.all_dirs.append(dirpath)
                self.check_empty_dir(dirpath)
                self.check_stale_project_dir(dirpath)

            for f in files:
                if f.startswith("."):
                    continue
                filepath = root_path / f
                if not filepath.is_file():
                    continue

                self.check_misplaced(filepath)
                self.check_stale(filepath)
                self.check_downloads(filepath)
                self.check_large(filepath)
                self.check_duplicate(filepath)

        self.find_similar_folders()
        self.duplicates = [(h, paths) for h, paths in self.file_hashes.items() if len(paths) > 1]

    def format_size(self, size: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def format_path(self, path: Path) -> str:
        try:
            return f"`~/{path.relative_to(self.scan_root)}`"
        except ValueError:
            return f"`{path}`"

    def generate_report(self) -> str:
        lines = [
            f"# Home Directory Audit",
            f"",
            f"**Generated:** {self.now.strftime('%Y-%m-%d %H:%M')}",
            f"**Scanned:** `{self.scan_root}`",
            f"",
            f"---",
            f"",
        ]

        if self.similar_folders:
            lines.append("## Similar Folder Names")
            lines.append("")
            for group in self.similar_folders:
                lines.append(f"- Potential duplicates:")
                for d in group:
                    lines.append(f"  - {self.format_path(d)}")
            lines.append("")

        if any(self.misplaced_files.values()):
            lines.append("## Misplaced Files")
            lines.append("")
            for category, files in self.misplaced_files.items():
                if files:
                    lines.append(f"### {category.title()} outside expected directories")
                    lines.append("")
                    for f in sorted(files)[:50]:
                        lines.append(f"- {self.format_path(f)}")
                    if len(files) > 50:
                        lines.append(f"- *...and {len(files) - 50} more*")
                    lines.append("")

        if self.old_downloads:
            lines.append("## Old Downloads (>30 days)")
            lines.append("")
            sorted_downloads = sorted(self.old_downloads, key=lambda x: x[1])[:50]
            for f, mtime in sorted_downloads:
                age = (self.now - mtime).days
                lines.append(f"- {self.format_path(f)} — {age} days old")
            if len(self.old_downloads) > 50:
                lines.append(f"- *...and {len(self.old_downloads) - 50} more*")
            lines.append("")

        if self.large_files:
            lines.append("## Large Files (>100 MB)")
            lines.append("")
            sorted_large = sorted(self.large_files, key=lambda x: -x[1])[:30]
            for f, size in sorted_large:
                lines.append(f"- {self.format_path(f)} — {self.format_size(size)}")
            if len(self.large_files) > 30:
                lines.append(f"- *...and {len(self.large_files) - 30} more*")
            lines.append("")

        if self.duplicates:
            lines.append("## Potential Duplicates")
            lines.append("")
            for h, paths in self.duplicates[:30]:
                size = self.get_size(paths[0])
                lines.append(f"- {self.format_size(size)} each:")
                for p in paths:
                    lines.append(f"  - {self.format_path(p)}")
            if len(self.duplicates) > 30:
                lines.append(f"- *...and {len(self.duplicates) - 30} more duplicate groups*")
            lines.append("")

        if self.empty_dirs:
            lines.append("## Empty Directories")
            lines.append("")
            for d in sorted(self.empty_dirs)[:50]:
                lines.append(f"- {self.format_path(d)}")
            if len(self.empty_dirs) > 50:
                lines.append(f"- *...and {len(self.empty_dirs) - 50} more*")
            lines.append("")

        if self.stale_project_dirs:
            lines.append("## Stale Project Directories (regenerable)")
            lines.append("")
            sorted_stale = sorted(self.stale_project_dirs, key=lambda x: -x[1])[:30]
            total_size = sum(s for _, s in self.stale_project_dirs)
            lines.append(f"*Total reclaimable: {self.format_size(total_size)}*")
            lines.append("")
            for d, size in sorted_stale:
                lines.append(f"- {self.format_path(d)} — {self.format_size(size)}")
            if len(self.stale_project_dirs) > 30:
                lines.append(f"- *...and {len(self.stale_project_dirs) - 30} more*")
            lines.append("")

        if self.stale_files:
            lines.append("## Stale Files (>180 days)")
            lines.append("")
            lines.append(f"*{len(self.stale_files)} files not modified in 180+ days*")
            lines.append("")
            sorted_stale = sorted(self.stale_files, key=lambda x: x[1])[:30]
            for f, mtime in sorted_stale:
                age = (self.now - mtime).days
                lines.append(f"- {self.format_path(f)} — {age} days")
            if len(self.stale_files) > 30:
                lines.append(f"- *...and {len(self.stale_files) - 30} more*")
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("## Summary")
        lines.append("")
        lines.append(f"| Issue | Count |")
        lines.append(f"|-------|-------|")
        lines.append(f"| Similar folders | {len(self.similar_folders)} |")
        lines.append(f"| Misplaced files | {sum(len(v) for v in self.misplaced_files.values())} |")
        lines.append(f"| Old downloads | {len(self.old_downloads)} |")
        lines.append(f"| Large files | {len(self.large_files)} |")
        lines.append(f"| Duplicate groups | {len(self.duplicates)} |")
        lines.append(f"| Empty directories | {len(self.empty_dirs)} |")
        lines.append(f"| Stale project dirs | {len(self.stale_project_dirs)} |")
        lines.append(f"| Stale files | {len(self.stale_files)} |")

        return "\n".join(lines)

    def save_report(self):
        report = self.generate_report()
        output_dir = CONFIG["output_dir"]
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"home-audit-{self.now.strftime('%Y-%m-%d')}.md"
        output_path = output_dir / filename

        output_path.write_text(report)
        print(f"Report saved to {output_path}")
        return output_path


def main():
    auditor = HomeAuditor()
    auditor.scan()
    auditor.save_report()


if __name__ == "__main__":
    main()
