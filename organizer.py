import os
import shutil
import argparse
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler

# --- Configuration ---

EXTENSION_MAP = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"],
    "Documents": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx", ".md"],
    "Archives": [".zip", ".tar", ".gz", ".rar", ".7z"],
    "Videos": [".mp4", ".mkv", ".avi", ".mov"],
    "Music": [".mp3", ".wav", ".aac", ".flac"],
    "Code": [".py", ".js", ".html", ".css", ".cpp", ".java", ".sh"],
    "Executables": [".exe", ".msi", ".deb", ".apk", ".bin", ".appimage"],
    "Others": []
}

FILE_TYPE_KEYWORDS = {
    "Executables": ["ELF", "executable", "PE32", "Mach-O"],
    "Documents": ["PDF", "Microsoft", "Word", "Excel", "PowerPoint", "Rich Text"],
    "Archives": ["archive", "compressed", "gzip", "bzip2"],
    "Images": ["image", "bitmap", "JPEG", "PNG"],
    "Videos": ["video", "AVI", "MP4", "Matroska"],
    "Music": ["audio", "MPEG ADTS", "FLAC", "WAV", "MP3"],
    "Code": ["ASCII text", "script", "source"]
}

DEFAULT_LOG_FILE = "organizer.log"


# --- Logger Setup ---

def setup_logger(log_file: str):
    logger = logging.getLogger("FileOrganizer")
    logger.setLevel(logging.DEBUG)

    handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=2)
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s]: %(message)s')
    handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(handler)

    return logger


# --- Core Functionality ---

class FileOrganizer:
    def __init__(self, target_dir: Path, dry_run: bool = False, logger=None):
        self.target_dir = target_dir.resolve()
        self.dry_run = dry_run
        self.logger = logger or setup_logger(DEFAULT_LOG_FILE)

    def organize(self):
        if not self.target_dir.exists() or not self.target_dir.is_dir():
            self.logger.error(f"Target directory does not exist or is not a directory: {self.target_dir}")
            return

        self.logger.info(f"Starting organization for: {self.target_dir} (dry-run={self.dry_run})")

        for entry in self.target_dir.iterdir():
            try:
                if entry.is_file():
                    self._process_file(entry)
            except Exception as e:
                self.logger.exception(f"Failed to process: {entry} - {e}")

    def _process_file(self, file_path: Path):
        if file_path.name.startswith('.'):
            self.logger.info(f"Skipping hidden file: {file_path.name}")
            return

        category = self._get_category_by_file_command(file_path)
        if not category:
            category = self._get_category_by_extension(file_path.suffix.lower())

        destination_folder = self.target_dir / category
        destination_folder.mkdir(exist_ok=True)

        new_path = self._resolve_conflict(destination_folder / file_path.name)

        if self.dry_run:
            self.logger.info(f"[DRY-RUN] Would move: {file_path.name} → {new_path}")
        else:
            shutil.move(str(file_path), str(new_path))
            self.logger.info(f"Moved: {file_path.name} → {new_path}")

    def _get_category_by_file_command(self, file_path: Path) -> str:
        try:
            result = subprocess.run(['file', '--brief', '--mime-type', str(file_path)],
                                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            mime_type = result.stdout.strip()
            result = subprocess.run(['file', str(file_path)],
                                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            full_output = result.stdout.lower()

            for category, keywords in FILE_TYPE_KEYWORDS.items():
                for keyword in keywords:
                    if keyword.lower() in full_output:
                        return category
        except Exception as e:
            self.logger.warning(f"Could not determine type using 'file' for {file_path.name}: {e}")

        return None

    def _get_category_by_extension(self, ext: str) -> str:
        for category, extensions in EXTENSION_MAP.items():
            if ext in extensions:
                return category
        return "Others"

    def _resolve_conflict(self, destination: Path) -> Path:
        if not destination.exists():
            return destination

        base = destination.stem
        ext = destination.suffix
        count = 1
        while True:
            new_name = f"{base}_{count}{ext}"
            new_path = destination.parent / new_name
            if not new_path.exists():
                return new_path
            count += 1


# --- CLI Interface ---

def main():
    parser = argparse.ArgumentParser(description="Powerful File Organizer Script with `file` command integration")
    parser.add_argument("directory", help="Target directory to organize")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without moving files")
    parser.add_argument("--log", default=DEFAULT_LOG_FILE, help="Path to log file")

    args = parser.parse_args()

    target_dir = Path(args.directory)
    logger = setup_logger(args.log)

    organizer = FileOrganizer(target_dir=target_dir, dry_run=args.dry_run, logger=logger)
    organizer.organize()


if __name__ == "__main__":
    main()
