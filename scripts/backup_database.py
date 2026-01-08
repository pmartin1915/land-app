"""
Database Backup Script

Creates timestamped backups of the SQLite database with optional compression.
Maintains configurable number of backup copies.

Usage:
    python scripts/backup_database.py                    # Create backup
    python scripts/backup_database.py --compress         # Create compressed backup
    python scripts/backup_database.py --keep 5           # Keep only last 5 backups
    python scripts/backup_database.py --list             # List existing backups
"""

import argparse
import shutil
import gzip
from datetime import datetime
from pathlib import Path
import sys

# Database location
DB_PATH = Path(__file__).parent.parent / "data" / "alabama_auction_watcher.db"
BACKUP_DIR = Path(__file__).parent.parent / "data" / "backups"


def get_backup_filename(compress: bool = False) -> str:
    """Generate timestamped backup filename."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = ".db.gz" if compress else ".db"
    return f"backup_{timestamp}{ext}"


def create_backup(compress: bool = False) -> Path:
    """
    Create a backup of the database.

    Args:
        compress: If True, compress the backup with gzip

    Returns:
        Path to the created backup file
    """
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        sys.exit(1)

    # Ensure backup directory exists
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    backup_filename = get_backup_filename(compress)
    backup_path = BACKUP_DIR / backup_filename

    if compress:
        # Compress while copying
        print(f"Creating compressed backup: {backup_path}")
        with open(DB_PATH, 'rb') as f_in:
            with gzip.open(backup_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
    else:
        # Simple copy
        print(f"Creating backup: {backup_path}")
        shutil.copy2(DB_PATH, backup_path)

    # Get file sizes
    original_size = DB_PATH.stat().st_size
    backup_size = backup_path.stat().st_size

    print(f"Original: {original_size / 1024 / 1024:.2f} MB")
    print(f"Backup: {backup_size / 1024 / 1024:.2f} MB")

    if compress:
        ratio = (1 - backup_size / original_size) * 100
        print(f"Compression: {ratio:.1f}% smaller")

    return backup_path


def list_backups() -> list[Path]:
    """List all existing backups sorted by date (newest first)."""
    if not BACKUP_DIR.exists():
        return []

    backups = list(BACKUP_DIR.glob("backup_*.db*"))
    return sorted(backups, key=lambda p: p.stat().st_mtime, reverse=True)


def cleanup_old_backups(keep: int):
    """
    Remove old backups, keeping only the most recent ones.

    Args:
        keep: Number of backups to keep
    """
    backups = list_backups()

    if len(backups) <= keep:
        print(f"Only {len(backups)} backups exist, keeping all")
        return

    to_remove = backups[keep:]
    print(f"Removing {len(to_remove)} old backups...")

    for backup in to_remove:
        print(f"  Removing: {backup.name}")
        backup.unlink()


def restore_backup(backup_path: Path):
    """
    Restore database from a backup.

    Args:
        backup_path: Path to backup file to restore
    """
    if not backup_path.exists():
        print(f"Error: Backup not found: {backup_path}")
        sys.exit(1)

    # Create a backup of current db first
    if DB_PATH.exists():
        pre_restore_backup = DB_PATH.with_suffix(".db.pre_restore")
        print(f"Backing up current database to: {pre_restore_backup}")
        shutil.copy2(DB_PATH, pre_restore_backup)

    # Restore
    if backup_path.suffix == ".gz":
        print(f"Restoring from compressed backup: {backup_path}")
        with gzip.open(backup_path, 'rb') as f_in:
            with open(DB_PATH, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
    else:
        print(f"Restoring from backup: {backup_path}")
        shutil.copy2(backup_path, DB_PATH)

    print(f"Restored database: {DB_PATH.stat().st_size / 1024 / 1024:.2f} MB")


def main():
    parser = argparse.ArgumentParser(description="Database backup utility")
    parser.add_argument("--compress", "-c", action="store_true",
                       help="Compress backup with gzip")
    parser.add_argument("--keep", "-k", type=int,
                       help="Keep only last N backups")
    parser.add_argument("--list", "-l", action="store_true",
                       help="List existing backups")
    parser.add_argument("--restore", "-r", type=str,
                       help="Restore from backup file (path or backup name)")

    args = parser.parse_args()

    if args.list:
        backups = list_backups()
        if not backups:
            print("No backups found")
        else:
            print(f"Found {len(backups)} backups in {BACKUP_DIR}:")
            for backup in backups:
                size_mb = backup.stat().st_size / 1024 / 1024
                mtime = datetime.fromtimestamp(backup.stat().st_mtime)
                print(f"  {backup.name} - {size_mb:.2f} MB - {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        return

    if args.restore:
        # Handle both full path and just filename
        restore_path = Path(args.restore)
        if not restore_path.exists():
            restore_path = BACKUP_DIR / args.restore
        restore_backup(restore_path)
        return

    # Create backup
    backup_path = create_backup(compress=args.compress)
    print(f"Backup created: {backup_path}")

    # Cleanup if requested
    if args.keep:
        cleanup_old_backups(args.keep)

    print("Done!")


if __name__ == "__main__":
    main()
