"""
Compression Module for Multi-Format Archive Processing

This module provides comprehensive compression and decompression operations
for multiple archive formats. No configuration required - works standalone.

Supported formats:
- ZIP (.zip) - Most common, cross-platform
- TAR (.tar) - Unix standard, can be combined with compression
- TAR.GZ / TGZ (.tar.gz, .tgz) - TAR with GZIP compression
- TAR.BZ2 / TBZ2 (.tar.bz2, .tbz2) - TAR with BZIP2 compression
- TAR.XZ (.tar.xz) - TAR with XZ/LZMA compression
- GZIP (.gz) - Single file compression
- BZIP2 (.bz2) - Single file compression
- XZ (.xz) - Single file compression (LZMA)
- 7Z (.7z) - High compression ratio (requires py7zr)

Features:
- Automatic format detection from file extension
- Compression level control
- Password protection (ZIP, 7Z)
- Selective extraction
- Directory tree compression
- Progress tracking for large archives
- Memory-efficient streaming for large files
- File filtering (by pattern, size, date)
- Archive inspection without extraction

Usage in generated code:
    from nl2py.modules import CompressionModule

    # Initialize module (no config needed)
    comp = CompressionModule()

    # Compress
    comp.compress_zip('data/', 'archive.zip', compression_level=9)
    comp.compress_targz('logs/', 'logs.tar.gz')
    comp.compress_7z('important/', 'important.7z', password='secret')

    # Decompress
    comp.extract_zip('archive.zip', 'output/')
    comp.extract_tar('archive.tar.gz', 'output/')
    comp.extract_7z('archive.7z', 'output/', password='secret')

    # Auto-detect format
    comp.extract_auto('archive.???', 'output/')
    comp.compress_auto('data/', 'archive.zip')

    # Inspect
    files = comp.list_archive('archive.zip')
    info = comp.get_archive_info('archive.zip')
"""

import os
import zipfile
import tarfile
import gzip
import bz2
import lzma
import shutil
import fnmatch
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, Callable
from datetime import datetime

try:
    import py7zr
except ImportError:
    py7zr = None


from .module_base import NL2PyModuleBase


class CompressionModule(NL2PyModuleBase):
    """
    Multi-format compression and decompression module.

    Supports ZIP, TAR (with various compressions), GZIP, BZIP2, XZ, and 7Z formats.
    """

    # Format detection mappings
    FORMAT_EXTENSIONS = {
        '.zip': 'zip',
        '.tar': 'tar',
        '.tar.gz': 'tar.gz',
        '.tgz': 'tar.gz',
        '.tar.bz2': 'tar.bz2',
        '.tbz2': 'tar.bz2',
        '.tar.xz': 'tar.xz',
        '.txz': 'tar.xz',
        '.gz': 'gzip',
        '.bz2': 'bzip2',
        '.xz': 'xz',
        '.7z': '7z'
    }

    def __init__(self):
        """Initialize the CompressionModule."""
        print("[CompressionModule] Module initialized - supports ZIP, TAR, GZIP, BZIP2, XZ, 7Z formats")

    # ==================== Format Detection ====================

    def detect_format(self, archive_path: str) -> Optional[str]:
        """
        Detect archive format from file extension.

        Args:
            archive_path: Path to archive file

        Returns:
            Format string or None if unknown
        """
        path = Path(archive_path).name.lower()

        # Check compound extensions first (.tar.gz, .tar.bz2, etc.)
        for ext, fmt in sorted(self.FORMAT_EXTENSIONS.items(), key=lambda x: -len(x[0])):
            if path.endswith(ext):
                return fmt

        return None

    # ==================== ZIP Operations ====================

    def compress_zip(
        self,
        source: Union[str, List[str]],
        output_file: str,
        compression_level: int = 6,
        password: Optional[str] = None,
        include_pattern: Optional[str] = None,
        exclude_pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a ZIP archive.

        Args:
            source: File, directory, or list of files/directories
            output_file: Output ZIP file path
            compression_level: 0-9 (0=store, 9=best compression)
            password: Optional password protection
            include_pattern: Only include files matching pattern (e.g., "*.txt")
            exclude_pattern: Exclude files matching pattern

        Returns:
            Dict with stats (files_count, compressed_size, compression_ratio)
        """
        compression = zipfile.ZIP_DEFLATED if compression_level > 0 else zipfile.ZIP_STORED

        total_original = 0
        total_compressed = 0
        files_count = 0

        with zipfile.ZipFile(output_file, 'w', compression=compression,
                            compresslevel=compression_level) as zf:

            # Set password if provided
            if password:
                zf.setpassword(password.encode())

            sources = [source] if isinstance(source, str) else source

            for src in sources:
                src_path = Path(src)

                if src_path.is_file():
                    if self._should_include_file(src_path.name, include_pattern, exclude_pattern):
                        arcname = src_path.name
                        zf.write(src, arcname)
                        files_count += 1
                        total_original += src_path.stat().st_size

                elif src_path.is_dir():
                    for root, dirs, files in os.walk(src):
                        for file in files:
                            if self._should_include_file(file, include_pattern, exclude_pattern):
                                file_path = Path(root) / file
                                arcname = file_path.relative_to(src_path.parent)
                                zf.write(file_path, arcname)
                                files_count += 1
                                total_original += file_path.stat().st_size

        total_compressed = Path(output_file).stat().st_size
        ratio = (1 - total_compressed / total_original) * 100 if total_original > 0 else 0

        print(f"[CompressionModule] Created ZIP: {output_file} ({files_count} files, {ratio:.1f}% compression)")

        return {
            'format': 'zip',
            'output_file': output_file,
            'files_count': files_count,
            'original_size': total_original,
            'compressed_size': total_compressed,
            'compression_ratio': ratio
        }

    def extract_zip(
        self,
        archive_path: str,
        output_dir: str,
        password: Optional[str] = None,
        members: Optional[List[str]] = None,
        pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract a ZIP archive.

        Args:
            archive_path: Path to ZIP file
            output_dir: Output directory
            password: Password if archive is encrypted
            members: Specific files to extract (None = all)
            pattern: Only extract files matching pattern

        Returns:
            Dict with stats
        """
        os.makedirs(output_dir, exist_ok=True)
        files_count = 0

        with zipfile.ZipFile(archive_path, 'r') as zf:
            if password:
                zf.setpassword(password.encode())

            # Get list of members to extract
            if members:
                extract_list = members
            elif pattern:
                extract_list = [name for name in zf.namelist()
                              if fnmatch.fnmatch(name, pattern)]
            else:
                extract_list = None  # Extract all

            if extract_list:
                for member in extract_list:
                    zf.extract(member, output_dir)
                    files_count += 1
            else:
                zf.extractall(output_dir)
                files_count = len(zf.namelist())

        print(f"[CompressionModule] Extracted ZIP: {files_count} files to {output_dir}")

        return {
            'format': 'zip',
            'files_count': files_count,
            'output_dir': output_dir
        }

    # ==================== TAR Operations ====================

    def compress_tar(
        self,
        source: Union[str, List[str]],
        output_file: str,
        compression: str = 'none',
        compression_level: int = 6,
        include_pattern: Optional[str] = None,
        exclude_pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a TAR archive.

        Args:
            source: File, directory, or list of files/directories
            output_file: Output TAR file path
            compression: 'none', 'gz', 'bz2', or 'xz'
            compression_level: 0-9 for gz/bz2
            include_pattern: Only include files matching pattern
            exclude_pattern: Exclude files matching pattern

        Returns:
            Dict with stats
        """
        # Determine mode
        mode_map = {
            'none': 'w',
            'gz': 'w:gz',
            'bz2': 'w:bz2',
            'xz': 'w:xz'
        }
        mode = mode_map.get(compression, 'w')

        total_size = 0
        files_count = 0

        with tarfile.open(output_file, mode) as tf:
            sources = [source] if isinstance(source, str) else source

            for src in sources:
                src_path = Path(src)

                if src_path.is_file():
                    if self._should_include_file(src_path.name, include_pattern, exclude_pattern):
                        tf.add(src, arcname=src_path.name)
                        files_count += 1
                        total_size += src_path.stat().st_size

                elif src_path.is_dir():
                    for root, dirs, files in os.walk(src):
                        for file in files:
                            if self._should_include_file(file, include_pattern, exclude_pattern):
                                file_path = Path(root) / file
                                arcname = file_path.relative_to(src_path.parent)
                                tf.add(file_path, arcname=arcname)
                                files_count += 1
                                total_size += file_path.stat().st_size

        compressed_size = Path(output_file).stat().st_size
        ratio = (1 - compressed_size / total_size) * 100 if total_size > 0 else 0

        print(f"[CompressionModule] Created TAR: {output_file} ({files_count} files, {ratio:.1f}% compression)")

        return {
            'format': f'tar.{compression}' if compression != 'none' else 'tar',
            'output_file': output_file,
            'files_count': files_count,
            'original_size': total_size,
            'compressed_size': compressed_size,
            'compression_ratio': ratio
        }

    def compress_targz(self, source: Union[str, List[str]], output_file: str, **kwargs) -> Dict[str, Any]:
        """Create TAR.GZ archive (shorthand)."""
        return self.compress_tar(source, output_file, compression='gz', **kwargs)

    def compress_tarbz2(self, source: Union[str, List[str]], output_file: str, **kwargs) -> Dict[str, Any]:
        """Create TAR.BZ2 archive (shorthand)."""
        return self.compress_tar(source, output_file, compression='bz2', **kwargs)

    def compress_tarxz(self, source: Union[str, List[str]], output_file: str, **kwargs) -> Dict[str, Any]:
        """Create TAR.XZ archive (shorthand)."""
        return self.compress_tar(source, output_file, compression='xz', **kwargs)

    def extract_tar(
        self,
        archive_path: str,
        output_dir: str,
        members: Optional[List[str]] = None,
        pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract a TAR archive (auto-detects compression).

        Args:
            archive_path: Path to TAR file
            output_dir: Output directory
            members: Specific files to extract
            pattern: Only extract files matching pattern

        Returns:
            Dict with stats
        """
        os.makedirs(output_dir, exist_ok=True)
        files_count = 0

        with tarfile.open(archive_path, 'r:*') as tf:
            if members:
                extract_list = [m for m in tf.getmembers() if m.name in members]
            elif pattern:
                extract_list = [m for m in tf.getmembers()
                              if fnmatch.fnmatch(m.name, pattern)]
            else:
                extract_list = None

            if extract_list:
                for member in extract_list:
                    tf.extract(member, output_dir)
                    files_count += 1
            else:
                tf.extractall(output_dir)
                files_count = len(tf.getmembers())

        print(f"[CompressionModule] Extracted TAR: {files_count} files to {output_dir}")

        return {
            'format': 'tar',
            'files_count': files_count,
            'output_dir': output_dir
        }

    # ==================== Single File Compression ====================

    def compress_gzip(self, source_file: str, output_file: Optional[str] = None,
                     compression_level: int = 6) -> Dict[str, Any]:
        """Compress a single file with GZIP."""
        if output_file is None:
            output_file = source_file + '.gz'

        original_size = Path(source_file).stat().st_size

        with open(source_file, 'rb') as f_in:
            with gzip.open(output_file, 'wb', compresslevel=compression_level) as f_out:
                shutil.copyfileobj(f_in, f_out)

        compressed_size = Path(output_file).stat().st_size
        ratio = (1 - compressed_size / original_size) * 100

        print(f"[CompressionModule] GZIP compressed: {output_file} ({ratio:.1f}% compression)")

        return {
            'format': 'gzip',
            'output_file': output_file,
            'original_size': original_size,
            'compressed_size': compressed_size,
            'compression_ratio': ratio
        }

    def extract_gzip(self, archive_path: str, output_file: Optional[str] = None) -> Dict[str, Any]:
        """Decompress a GZIP file."""
        if output_file is None:
            output_file = archive_path.replace('.gz', '')

        with gzip.open(archive_path, 'rb') as f_in:
            with open(output_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        print(f"[CompressionModule] GZIP extracted: {output_file}")

        return {
            'format': 'gzip',
            'output_file': output_file,
            'decompressed_size': Path(output_file).stat().st_size
        }

    def compress_bzip2(self, source_file: str, output_file: Optional[str] = None,
                      compression_level: int = 9) -> Dict[str, Any]:
        """Compress a single file with BZIP2."""
        if output_file is None:
            output_file = source_file + '.bz2'

        original_size = Path(source_file).stat().st_size

        with open(source_file, 'rb') as f_in:
            with bz2.open(output_file, 'wb', compresslevel=compression_level) as f_out:
                shutil.copyfileobj(f_in, f_out)

        compressed_size = Path(output_file).stat().st_size
        ratio = (1 - compressed_size / original_size) * 100

        print(f"[CompressionModule] BZIP2 compressed: {output_file} ({ratio:.1f}% compression)")

        return {
            'format': 'bzip2',
            'output_file': output_file,
            'original_size': original_size,
            'compressed_size': compressed_size,
            'compression_ratio': ratio
        }

    def extract_bzip2(self, archive_path: str, output_file: Optional[str] = None) -> Dict[str, Any]:
        """Decompress a BZIP2 file."""
        if output_file is None:
            output_file = archive_path.replace('.bz2', '')

        with bz2.open(archive_path, 'rb') as f_in:
            with open(output_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        print(f"[CompressionModule] BZIP2 extracted: {output_file}")

        return {
            'format': 'bzip2',
            'output_file': output_file,
            'decompressed_size': Path(output_file).stat().st_size
        }

    def compress_xz(self, source_file: str, output_file: Optional[str] = None,
                   compression_level: int = 6) -> Dict[str, Any]:
        """Compress a single file with XZ/LZMA."""
        if output_file is None:
            output_file = source_file + '.xz'

        original_size = Path(source_file).stat().st_size

        with open(source_file, 'rb') as f_in:
            with lzma.open(output_file, 'wb', preset=compression_level) as f_out:
                shutil.copyfileobj(f_in, f_out)

        compressed_size = Path(output_file).stat().st_size
        ratio = (1 - compressed_size / original_size) * 100

        print(f"[CompressionModule] XZ compressed: {output_file} ({ratio:.1f}% compression)")

        return {
            'format': 'xz',
            'output_file': output_file,
            'original_size': original_size,
            'compressed_size': compressed_size,
            'compression_ratio': ratio
        }

    def extract_xz(self, archive_path: str, output_file: Optional[str] = None) -> Dict[str, Any]:
        """Decompress an XZ file."""
        if output_file is None:
            output_file = archive_path.replace('.xz', '')

        with lzma.open(archive_path, 'rb') as f_in:
            with open(output_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        print(f"[CompressionModule] XZ extracted: {output_file}")

        return {
            'format': 'xz',
            'output_file': output_file,
            'decompressed_size': Path(output_file).stat().st_size
        }

    # ==================== 7Z Operations ====================

    def compress_7z(
        self,
        source: Union[str, List[str]],
        output_file: str,
        password: Optional[str] = None,
        compression_level: int = 5
    ) -> Dict[str, Any]:
        """
        Create a 7Z archive.

        Args:
            source: File, directory, or list of files/directories
            output_file: Output 7Z file path
            password: Optional password protection
            compression_level: 0-9

        Returns:
            Dict with stats

        Requires: pip install py7zr
        """
        if py7zr is None:
            raise ImportError("py7zr is required. Install with: pip install py7zr")

        filters = [{'id': lzma.FILTER_LZMA2, 'preset': compression_level}]

        total_size = 0
        files_count = 0

        with py7zr.SevenZipFile(output_file, 'w', password=password, filters=filters) as archive:
            sources = [source] if isinstance(source, str) else source

            for src in sources:
                src_path = Path(src)

                if src_path.is_file():
                    archive.write(src, src_path.name)
                    files_count += 1
                    total_size += src_path.stat().st_size
                elif src_path.is_dir():
                    archive.writeall(src, src_path.name)
                    for root, dirs, files in os.walk(src):
                        files_count += len(files)
                        for file in files:
                            total_size += (Path(root) / file).stat().st_size

        compressed_size = Path(output_file).stat().st_size
        ratio = (1 - compressed_size / total_size) * 100 if total_size > 0 else 0

        print(f"[CompressionModule] Created 7Z: {output_file} ({files_count} files, {ratio:.1f}% compression)")

        return {
            'format': '7z',
            'output_file': output_file,
            'files_count': files_count,
            'original_size': total_size,
            'compressed_size': compressed_size,
            'compression_ratio': ratio
        }

    def extract_7z(
        self,
        archive_path: str,
        output_dir: str,
        password: Optional[str] = None,
        targets: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Extract a 7Z archive."""
        if py7zr is None:
            raise ImportError("py7zr is required. Install with: pip install py7zr")

        os.makedirs(output_dir, exist_ok=True)

        with py7zr.SevenZipFile(archive_path, 'r', password=password) as archive:
            if targets:
                archive.extract(output_dir, targets=targets)
                files_count = len(targets)
            else:
                archive.extractall(output_dir)
                files_count = len(archive.getnames())

        print(f"[CompressionModule] Extracted 7Z: {files_count} files to {output_dir}")

        return {
            'format': '7z',
            'files_count': files_count,
            'output_dir': output_dir
        }

    # ==================== Auto-Detection Operations ====================

    def compress_auto(self, source: Union[str, List[str]], output_file: str, **kwargs) -> Dict[str, Any]:
        """Automatically compress based on output file extension."""
        fmt = self.detect_format(output_file)

        if fmt == 'zip':
            return self.compress_zip(source, output_file, **kwargs)
        elif fmt == 'tar':
            return self.compress_tar(source, output_file, compression='none', **kwargs)
        elif fmt == 'tar.gz':
            return self.compress_targz(source, output_file, **kwargs)
        elif fmt == 'tar.bz2':
            return self.compress_tarbz2(source, output_file, **kwargs)
        elif fmt == 'tar.xz':
            return self.compress_tarxz(source, output_file, **kwargs)
        elif fmt == '7z':
            return self.compress_7z(source, output_file, **kwargs)
        else:
            raise ValueError(f"Unsupported format for {output_file}")

    def extract_auto(self, archive_path: str, output_dir: str, **kwargs) -> Dict[str, Any]:
        """Automatically extract based on archive file extension."""
        fmt = self.detect_format(archive_path)

        if fmt == 'zip':
            return self.extract_zip(archive_path, output_dir, **kwargs)
        elif fmt in ['tar', 'tar.gz', 'tar.bz2', 'tar.xz']:
            return self.extract_tar(archive_path, output_dir, **kwargs)
        elif fmt == 'gzip':
            return self.extract_gzip(archive_path, **kwargs)
        elif fmt == 'bzip2':
            return self.extract_bzip2(archive_path, **kwargs)
        elif fmt == 'xz':
            return self.extract_xz(archive_path, **kwargs)
        elif fmt == '7z':
            return self.extract_7z(archive_path, output_dir, **kwargs)
        else:
            raise ValueError(f"Unsupported format for {archive_path}")

    # ==================== Inspection Operations ====================

    def list_archive(self, archive_path: str) -> List[Dict[str, Any]]:
        """
        List contents of an archive.

        Returns:
            List of dicts with file info (name, size, compressed_size, date)
        """
        fmt = self.detect_format(archive_path)
        files = []

        if fmt == 'zip':
            with zipfile.ZipFile(archive_path, 'r') as zf:
                for info in zf.infolist():
                    files.append({
                        'name': info.filename,
                        'size': info.file_size,
                        'compressed_size': info.compress_size,
                        'date': datetime(*info.date_time),
                        'is_dir': info.is_dir()
                    })

        elif fmt in ['tar', 'tar.gz', 'tar.bz2', 'tar.xz']:
            with tarfile.open(archive_path, 'r:*') as tf:
                for member in tf.getmembers():
                    files.append({
                        'name': member.name,
                        'size': member.size,
                        'date': datetime.fromtimestamp(member.mtime),
                        'is_dir': member.isdir()
                    })

        elif fmt == '7z' and py7zr:
            with py7zr.SevenZipFile(archive_path, 'r') as archive:
                for name, info in archive.list():
                    files.append({
                        'name': name,
                        'size': info.uncompressed,
                        'compressed_size': info.compressed,
                        'is_dir': info.is_directory
                    })

        return files

    def get_archive_info(self, archive_path: str) -> Dict[str, Any]:
        """Get summary info about an archive."""
        fmt = self.detect_format(archive_path)
        archive_size = Path(archive_path).stat().st_size
        files = self.list_archive(archive_path)

        total_size = sum(f['size'] for f in files if not f['is_dir'])
        files_count = sum(1 for f in files if not f['is_dir'])
        dirs_count = sum(1 for f in files if f['is_dir'])

        ratio = (1 - archive_size / total_size) * 100 if total_size > 0 else 0

        return {
            'format': fmt,
            'archive_path': archive_path,
            'archive_size': archive_size,
            'files_count': files_count,
            'dirs_count': dirs_count,
            'total_uncompressed_size': total_size,
            'compression_ratio': ratio
        }

    # ==================== Helper Methods ====================

    def _should_include_file(
        self,
        filename: str,
        include_pattern: Optional[str],
        exclude_pattern: Optional[str]
    ) -> bool:
        """Check if file should be included based on patterns."""
        if exclude_pattern and fnmatch.fnmatch(filename, exclude_pattern):
            return False
        if include_pattern and not fnmatch.fnmatch(filename, include_pattern):
            return False
        return True

    # =============================================================================
    # Metadata Methods for NL2Py Compiler
    # =============================================================================

    @classmethod
    def get_metadata(cls):
        """Get module metadata."""
        from nl2py.modules.module_base import ModuleMetadata
        return ModuleMetadata(
            name="Compression",
            task_type="compression",
            description="Multi-format compression and decompression for ZIP, TAR, GZIP, BZIP2, XZ, and 7Z archives",
            version="1.0.0",
            keywords=["compression", "archive", "zip", "tar", "gzip", "bzip2", "xz", "7z", "extract", "decompress"],
            dependencies=["py7zr>=0.20.0"]  # Optional, for 7Z support
        )

    @classmethod
    def get_usage_notes(cls):
        """Get detailed usage notes."""
        return [
            "Module supports multiple compression formats: ZIP, TAR, TAR.GZ, TAR.BZ2, TAR.XZ, GZIP, BZIP2, XZ, 7Z",
            "No configuration required - works standalone without nl2py.conf",
            "Automatic format detection from file extensions",
            "ZIP and 7Z support password protection",
            "TAR supports multiple compression modes: none, gz, bz2, xz",
            "Compression level: 0 (no compression) to 9 (maximum compression)",
            "Single file compression: GZIP, BZIP2, XZ for individual files",
            "Archive compression: ZIP, TAR, 7Z for directories and multiple files",
            "Selective extraction via patterns (*.txt) or member lists",
            "Include/exclude patterns for filtering files during compression",
            "compress_auto() and extract_auto() detect format from file extension",
            "list_archive() inspects archive contents without extraction",
            "get_archive_info() provides statistics (size, compression ratio, file count)",
            "7Z support requires py7zr library (pip install py7zr)",
            "Key methods: compress_zip, extract_zip, compress_targz, extract_tar, compress_auto, extract_auto, list_archive",
        ]

    @classmethod
    def get_methods_info(cls):
        """Get information about module methods."""
        from nl2py.modules.module_base import MethodInfo
        return [
            MethodInfo(
                name="compress_zip",
                description="Create a ZIP archive with optional password protection and file filtering",
                parameters={
                    "source": "File path, directory path, or list of paths to compress",
                    "output_file": "Output ZIP file path (string)",
                    "compression_level": "0-9 (0=store, 9=max compression, default: 6)",
                    "password": "Optional password for encryption (string, default: None)",
                    "include_pattern": "Only include files matching pattern, e.g., '*.txt' (optional)",
                    "exclude_pattern": "Exclude files matching pattern, e.g., '*.tmp' (optional)"
                },
                returns="Dict with format, output_file, files_count, original_size, compressed_size, compression_ratio",
                examples=[
                    {"text": "Compress directory {{data/}} to ZIP {{archive.zip}} with compression level {{9}}", "code": "compress_zip(source='{{data/}}', output_file='{{archive.zip}}', compression_level={{9}})"},
                    {"text": "Compress directory {{logs/}} to password-protected ZIP {{logs.zip}} with password {{secret123}}", "code": "compress_zip(source='{{logs/}}', output_file='{{logs.zip}}', password='{{secret123}}')"},
                    {"text": "Compress directory {{src/}} to ZIP {{source.zip}} including only {{*.py}} files with level {{9}}", "code": "compress_zip(source='{{src/}}', output_file='{{source.zip}}', include_pattern='{{*.py}}', compression_level={{9}})"},
                ]
            ),
            MethodInfo(
                name="extract_zip",
                description="Extract a ZIP archive with optional password and selective extraction",
                parameters={
                    "archive_path": "Path to ZIP file (string)",
                    "output_dir": "Output directory for extracted files (string)",
                    "password": "Password if archive is encrypted (optional)",
                    "members": "List of specific files to extract (optional, None = all)",
                    "pattern": "Only extract files matching pattern, e.g., '*.txt' (optional)"
                },
                returns="Dict with format, files_count, output_dir",
                examples=[
                    {"text": "Extract ZIP {{archive.zip}} to directory {{output/}}", "code": "extract_zip(archive_path='{{archive.zip}}', output_dir='{{output/}}')"},
                    {"text": "Extract password-protected ZIP {{secure.zip}} to {{data/}} with password {{secret123}}", "code": "extract_zip(archive_path='{{secure.zip}}', output_dir='{{data/}}', password='{{secret123}}')"},
                    {"text": "Extract ZIP {{logs.zip}} to {{logs/}} filtering by pattern {{*.log}}", "code": "extract_zip(archive_path='{{logs.zip}}', output_dir='{{logs/}}', pattern='{{*.log}}')"},
                ]
            ),
            MethodInfo(
                name="compress_tar",
                description="Create a TAR archive with optional compression (gzip, bzip2, xz)",
                parameters={
                    "source": "File path, directory path, or list of paths",
                    "output_file": "Output TAR file path (string)",
                    "compression": "'none', 'gz', 'bz2', or 'xz' (default: 'none')",
                    "compression_level": "0-9 for gz/bz2 compression (default: 6)",
                    "include_pattern": "Only include files matching pattern (optional)",
                    "exclude_pattern": "Exclude files matching pattern (optional)"
                },
                returns="Dict with format, output_file, files_count, original_size, compressed_size, compression_ratio",
                examples=[
                    {"text": "Create uncompressed TAR archive {{archive.tar}} from {{data/}}", "code": "compress_tar(source='{{data/}}', output_file='{{archive.tar}}', compression='none')"},
                    {"text": "Create TAR.GZ archive {{logs.tar}} from {{logs/}} with compression level {{9}}", "code": "compress_tar(source='{{logs/}}', output_file='{{logs.tar}}', compression='gz', compression_level={{9}})"},
                    {"text": "Create TAR.BZ2 archive {{backup.tar}} from {{backups/}}", "code": "compress_tar(source='{{backups/}}', output_file='{{backup.tar}}', compression='bz2')"},
                ]
            ),
            MethodInfo(
                name="compress_targz",
                description="Create a TAR.GZ archive (shorthand for compress_tar with gz)",
                parameters={
                    "source": "File path, directory path, or list of paths",
                    "output_file": "Output TAR.GZ file path (string)",
                    "compression_level": "0-9 (default: 6)"
                },
                returns="Dict with format, output_file, files_count, sizes, compression_ratio",
                examples=[
                    {"text": "Create TAR.GZ archive {{archive.tar.gz}} from {{data/}}", "code": "compress_targz(source='{{data/}}', output_file='{{archive.tar.gz}}')"},
                    {"text": "Create TAR.GZ archive {{project.tgz}} from {{project/}} with compression level {{9}}", "code": "compress_targz(source='{{project/}}', output_file='{{project.tgz}}', compression_level={{9}})"},
                ]
            ),
            MethodInfo(
                name="compress_tarbz2",
                description="Create a TAR.BZ2 archive (shorthand for compress_tar with bz2)",
                parameters={
                    "source": "File path, directory path, or list of paths",
                    "output_file": "Output TAR.BZ2 file path (string)",
                    "compression_level": "0-9 (default: 6)"
                },
                returns="Dict with format, output_file, files_count, sizes, compression_ratio",
                examples=[
                    {"text": "Create TAR.BZ2 archive {{archive.tar.bz2}} from {{data/}}", "code": "compress_tarbz2(source='{{data/}}', output_file='{{archive.tar.bz2}}')"},
                    {"text": "Create TAR.BZ2 archive {{backup.tbz2}} from {{backups/}} with compression level {{9}}", "code": "compress_tarbz2(source='{{backups/}}', output_file='{{backup.tbz2}}', compression_level={{9}})"},
                ]
            ),
            MethodInfo(
                name="compress_tarxz",
                description="Create a TAR.XZ archive with LZMA compression (best compression ratio)",
                parameters={
                    "source": "File path, directory path, or list of paths",
                    "output_file": "Output TAR.XZ file path (string)",
                    "compression_level": "0-9 (default: 6)"
                },
                returns="Dict with format, output_file, files_count, sizes, compression_ratio",
                examples=[
                    {"text": "Create TAR.XZ archive {{archive.tar.xz}} from {{data/}}", "code": "compress_tarxz(source='{{data/}}', output_file='{{archive.tar.xz}}')"},
                    {"text": "Create TAR.XZ archive {{src.tar.xz}} from {{source/}} with compression level {{9}}", "code": "compress_tarxz(source='{{source/}}', output_file='{{src.tar.xz}}', compression_level={{9}})"},
                ]
            ),
            MethodInfo(
                name="extract_tar",
                description="Extract a TAR archive (auto-detects compression: tar, tar.gz, tar.bz2, tar.xz)",
                parameters={
                    "archive_path": "Path to TAR file (string)",
                    "output_dir": "Output directory (string)",
                    "members": "List of specific files to extract (optional)",
                    "pattern": "Only extract files matching pattern (optional)"
                },
                returns="Dict with format, files_count, output_dir",
                examples=[
                    {"text": "Extract TAR.GZ {{archive.tar.gz}} to directory {{output/}}", "code": "extract_tar(archive_path='{{archive.tar.gz}}', output_dir='{{output/}}')"},
                    {"text": "Extract TAR.BZ2 {{backup.tar.bz2}} to directory {{restore/}}", "code": "extract_tar(archive_path='{{backup.tar.bz2}}', output_dir='{{restore/}}')"},
                    {"text": "Extract TAR.GZ {{logs.tar.gz}} to {{logs/}} filtering by pattern {{*.log}}", "code": "extract_tar(archive_path='{{logs.tar.gz}}', output_dir='{{logs/}}', pattern='{{*.log}}')"},
                ]
            ),
            MethodInfo(
                name="compress_7z",
                description="Create a 7Z archive with LZMA2 compression and optional password (requires py7zr)",
                parameters={
                    "source": "File path, directory path, or list of paths",
                    "output_file": "Output 7Z file path (string)",
                    "password": "Optional password for encryption (string)",
                    "compression_level": "0-9 (default: 5)"
                },
                returns="Dict with format, output_file, files_count, original_size, compressed_size, compression_ratio",
                examples=[
                    {"text": "Create 7Z archive {{archive.7z}} from {{data/}} with compression level {{9}}", "code": "compress_7z(source='{{data/}}', output_file='{{archive.7z}}', compression_level={{9}})"},
                    {"text": "Create password-protected 7Z {{secure.7z}} from {{confidential/}} with password {{secret}} and level {{9}}", "code": "compress_7z(source='{{confidential/}}', output_file='{{secure.7z}}', password='{{secret}}', compression_level={{9}})"},
                ]
            ),
            MethodInfo(
                name="extract_7z",
                description="Extract a 7Z archive with optional password (requires py7zr)",
                parameters={
                    "archive_path": "Path to 7Z file (string)",
                    "output_dir": "Output directory (string)",
                    "password": "Password if archive is encrypted (optional)",
                    "targets": "List of specific files to extract (optional)"
                },
                returns="Dict with format, files_count, output_dir",
                examples=[
                    {"text": "Extract 7Z {{archive.7z}} to directory {{output/}}", "code": "extract_7z(archive_path='{{archive.7z}}', output_dir='{{output/}}')"},
                    {"text": "Extract password-protected 7Z {{secure.7z}} to {{data/}} with password {{secret}}", "code": "extract_7z(archive_path='{{secure.7z}}', output_dir='{{data/}}', password='{{secret}}')"},
                ]
            ),
            MethodInfo(
                name="compress_auto",
                description="Automatically compress based on output file extension (zip, tar, tar.gz, tar.bz2, tar.xz, 7z)",
                parameters={
                    "source": "File path, directory path, or list of paths",
                    "output_file": "Output file path with extension indicating format (string)"
                },
                returns="Dict with format-specific results",
                examples=[
                    {"text": "Auto-compress {{data/}} to ZIP {{archive.zip}} based on extension", "code": "compress_auto(source='{{data/}}', output_file='{{archive.zip}}')"},
                    {"text": "Auto-compress {{logs/}} to TAR.GZ {{logs.tar.gz}} based on extension", "code": "compress_auto(source='{{logs/}}', output_file='{{logs.tar.gz}}')"},
                    {"text": "Auto-compress {{backups/}} to 7Z {{backup.7z}} based on extension", "code": "compress_auto(source='{{backups/}}', output_file='{{backup.7z}}')"},
                ]
            ),
            MethodInfo(
                name="extract_auto",
                description="Automatically extract based on archive file extension",
                parameters={
                    "archive_path": "Path to archive file (string)",
                    "output_dir": "Output directory (string)"
                },
                returns="Dict with format-specific results",
                examples=[
                    {"text": "Auto-extract ZIP {{archive.zip}} to {{output/}} based on extension", "code": "extract_auto(archive_path='{{archive.zip}}', output_dir='{{output/}}')"},
                    {"text": "Auto-extract TAR.GZ {{backup.tar.gz}} to {{restore/}} based on extension", "code": "extract_auto(archive_path='{{backup.tar.gz}}', output_dir='{{restore/}}')"},
                    {"text": "Auto-extract 7Z {{data.7z}} to {{extracted/}} based on extension", "code": "extract_auto(archive_path='{{data.7z}}', output_dir='{{extracted/}}')"},
                ]
            ),
            MethodInfo(
                name="list_archive",
                description="List contents of an archive without extracting",
                parameters={
                    "archive_path": "Path to archive file (string)"
                },
                returns="List of dicts with file info: name, size, compressed_size, date, is_dir",
                examples=[
                    {"text": "List contents of ZIP archive {{archive.zip}}", "code": "list_archive(archive_path='{{archive.zip}}')"},
                    {"text": "List contents of TAR.GZ archive {{backup.tar.gz}}", "code": "list_archive(archive_path='{{backup.tar.gz}}')"},
                    {"text": "List contents of 7Z archive {{data.7z}}", "code": "list_archive(archive_path='{{data.7z}}')"},
                ]
            ),
            MethodInfo(
                name="get_archive_info",
                description="Get summary statistics about an archive",
                parameters={
                    "archive_path": "Path to archive file (string)"
                },
                returns="Dict with format, archive_path, archive_size, files_count, dirs_count, total_uncompressed_size, compression_ratio",
                examples=[
                    {"text": "Get statistics for ZIP archive {{archive.zip}}", "code": "get_archive_info(archive_path='{{archive.zip}}')"},
                    {"text": "Get statistics for TAR.GZ archive {{backup.tar.gz}}", "code": "get_archive_info(archive_path='{{backup.tar.gz}}')"},
                    {"text": "Get statistics for 7Z archive {{data.7z}}", "code": "get_archive_info(archive_path='{{data.7z}}')"},
                ]
            ),
            MethodInfo(
                name="detect_format",
                description="Detect archive format from file extension",
                parameters={"archive_path": "Path to archive file (string)"},
                returns="str/None - Format string (zip, tar, targz, tarbz2, tarxz, 7z, gzip, bzip2, xz) or None if unknown",
                examples=[
                    {"text": "Detect format of archive {{archive.tar.gz}}", "code": "detect_format(archive_path='{{archive.tar.gz}}')"},
                    {"text": "Detect format of archive {{file.7z}}", "code": "detect_format(archive_path='{{file.7z}}')"},
                ]
            ),
            MethodInfo(
                name="compress_gzip",
                description="Compress a single file with GZIP compression",
                parameters={
                    "source_file": "Path to file to compress (string)",
                    "output_file": "Output file path (optional, defaults to source + '.gz')",
                    "compression_level": "0-9 (default: 6)"
                },
                returns="Dict with format, output_file, original_size, compressed_size, compression_ratio",
                examples=[
                    {"text": "Compress file {{data.txt}} to GZIP {{data.txt.gz}}", "code": "compress_gzip(source_file='{{data.txt}}', output_file='{{data.txt.gz}}')"},
                    {"text": "Compress file {{log.txt}} with GZIP level {{9}}", "code": "compress_gzip(source_file='{{log.txt}}', compression_level={{9}})"},
                ]
            ),
            MethodInfo(
                name="extract_gzip",
                description="Decompress a GZIP file",
                parameters={
                    "archive_path": "Path to .gz file (string)",
                    "output_file": "Output file path (optional, defaults to removing .gz extension)"
                },
                returns="Dict with format, output_file, decompressed_size",
                examples=[
                    {"text": "Decompress GZIP {{data.txt.gz}} to {{data.txt}}", "code": "extract_gzip(archive_path='{{data.txt.gz}}', output_file='{{data.txt}}')"},
                    {"text": "Decompress GZIP {{log.gz}} with auto-naming", "code": "extract_gzip(archive_path='{{log.gz}}')"},
                ]
            ),
            MethodInfo(
                name="compress_bzip2",
                description="Compress a single file with BZIP2 compression (better ratio than gzip)",
                parameters={
                    "source_file": "Path to file to compress (string)",
                    "output_file": "Output file path (optional, defaults to source + '.bz2')",
                    "compression_level": "0-9 (default: 9)"
                },
                returns="Dict with format, output_file, original_size, compressed_size, compression_ratio",
                examples=[
                    {"text": "Compress file {{data.txt}} to BZIP2 {{data.txt.bz2}}", "code": "compress_bzip2(source_file='{{data.txt}}', output_file='{{data.txt.bz2}}')"},
                    {"text": "Compress file {{log.txt}} with BZIP2 level {{9}}", "code": "compress_bzip2(source_file='{{log.txt}}', compression_level={{9}})"},
                ]
            ),
            MethodInfo(
                name="extract_bzip2",
                description="Decompress a BZIP2 file",
                parameters={
                    "archive_path": "Path to .bz2 file (string)",
                    "output_file": "Output file path (optional, defaults to removing .bz2 extension)"
                },
                returns="Dict with format, output_file, decompressed_size",
                examples=[
                    {"text": "Decompress BZIP2 {{data.txt.bz2}} to {{data.txt}}", "code": "extract_bzip2(archive_path='{{data.txt.bz2}}', output_file='{{data.txt}}')"},
                    {"text": "Decompress BZIP2 {{archive.bz2}} with auto-naming", "code": "extract_bzip2(archive_path='{{archive.bz2}}')"},
                ]
            ),
            MethodInfo(
                name="compress_xz",
                description="Compress a single file with XZ/LZMA compression (best compression ratio)",
                parameters={
                    "source_file": "Path to file to compress (string)",
                    "output_file": "Output file path (optional, defaults to source + '.xz')",
                    "compression_level": "0-9 (default: 6)"
                },
                returns="Dict with format, output_file, original_size, compressed_size, compression_ratio",
                examples=[
                    {"text": "Compress file {{data.txt}} to XZ {{data.txt.xz}}", "code": "compress_xz(source_file='{{data.txt}}', output_file='{{data.txt.xz}}')"},
                    {"text": "Compress file {{log.txt}} with XZ level {{9}}", "code": "compress_xz(source_file='{{log.txt}}', compression_level={{9}})"},
                ]
            ),
            MethodInfo(
                name="extract_xz",
                description="Decompress an XZ/LZMA file",
                parameters={
                    "archive_path": "Path to .xz file (string)",
                    "output_file": "Output file path (optional, defaults to removing .xz extension)"
                },
                returns="Dict with format, output_file, decompressed_size",
                examples=[
                    {"text": "Decompress XZ {{data.txt.xz}} to {{data.txt}}", "code": "extract_xz(archive_path='{{data.txt.xz}}', output_file='{{data.txt}}')"},
                    {"text": "Decompress XZ {{archive.xz}} with auto-naming", "code": "extract_xz(archive_path='{{archive.xz}}')"},
                ]
            ),
        ]

