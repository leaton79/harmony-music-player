"""
Metadata module for reading and writing audio file tags.
Supports MP3, FLAC, AAC, WAV, OGG, and other formats via mutagen.
"""

import os
from pathlib import Path
from typing import Dict, Optional, List, Tuple
import hashlib
import struct

try:
    from mutagen import File as MutagenFile
    from mutagen.mp3 import MP3
    from mutagen.flac import FLAC
    from mutagen.mp4 import MP4
    from mutagen.oggvorbis import OggVorbis
    from mutagen.wave import WAVE
    from mutagen.aiff import AIFF
    from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TCON, TDRC, TRCK, TPE2, TPOS
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False


# Supported audio formats
SUPPORTED_FORMATS = {
    '.mp3': 'MP3',
    '.flac': 'FLAC',
    '.m4a': 'AAC',
    '.mp4': 'AAC',
    '.aac': 'AAC',
    '.ogg': 'OGG Vorbis',
    '.wav': 'WAV',
    '.aiff': 'AIFF',
    '.aif': 'AIFF',
    '.wma': 'WMA',
    '.opus': 'Opus',
}


class MetadataReader:
    """Reads metadata from audio files."""
    
    def __init__(self, cover_art_dir: str = None):
        if not MUTAGEN_AVAILABLE:
            raise ImportError("mutagen library is required. Install with: pip install mutagen")
        
        if cover_art_dir is None:
            cover_art_dir = str(Path.home() / ".harmony_player" / "artwork")
        
        self.cover_art_dir = Path(cover_art_dir)
        self.cover_art_dir.mkdir(parents=True, exist_ok=True)
    
    def is_supported(self, file_path: str) -> bool:
        """Check if file format is supported."""
        ext = Path(file_path).suffix.lower()
        return ext in SUPPORTED_FORMATS
    
    def read_metadata(self, file_path: str) -> Optional[Dict]:
        """Read metadata from an audio file."""
        if not os.path.exists(file_path):
            return None
        
        if not self.is_supported(file_path):
            return None
        
        try:
            audio = MutagenFile(file_path, easy=True)
            if audio is None:
                return self._read_basic_info(file_path)
            
            # Get file info
            file_stat = os.stat(file_path)
            ext = Path(file_path).suffix.lower()
            
            metadata = {
                'file_path': file_path,
                'file_format': SUPPORTED_FORMATS.get(ext, 'Unknown'),
                'file_size': file_stat.st_size,
                'duration': getattr(audio.info, 'length', 0) if audio.info else 0,
                'bitrate': getattr(audio.info, 'bitrate', 0) if audio.info else 0,
                'sample_rate': getattr(audio.info, 'sample_rate', 0) if audio.info else 0,
            }
            
            # Read standard tags (easy mode)
            tag_mapping = {
                'title': 'title',
                'artist': 'artist',
                'album': 'album',
                'albumartist': 'album_artist',
                'genre': 'genre',
                'date': 'year',
                'tracknumber': 'track_number',
                'discnumber': 'disc_number',
            }
            
            for tag_key, meta_key in tag_mapping.items():
                if audio and tag_key in audio:
                    value = audio[tag_key][0] if audio[tag_key] else None
                    if meta_key in ('year', 'track_number', 'disc_number'):
                        value = self._parse_number(value)
                    metadata[meta_key] = value
                else:
                    metadata[meta_key] = None
            
            # Set title to filename if missing
            if not metadata.get('title'):
                metadata['title'] = Path(file_path).stem
            
            # Extract cover art
            cover_path = self._extract_cover_art(file_path)
            metadata['cover_art_path'] = cover_path
            
            return metadata
            
        except Exception as e:
            print(f"Error reading metadata from {file_path}: {e}")
            return self._read_basic_info(file_path)
    
    def _read_basic_info(self, file_path: str) -> Dict:
        """Read basic file info when metadata reading fails."""
        file_stat = os.stat(file_path)
        ext = Path(file_path).suffix.lower()
        
        return {
            'file_path': file_path,
            'title': Path(file_path).stem,
            'artist': None,
            'album': None,
            'album_artist': None,
            'genre': None,
            'year': None,
            'track_number': None,
            'disc_number': None,
            'duration': 0,
            'bitrate': 0,
            'sample_rate': 0,
            'file_format': SUPPORTED_FORMATS.get(ext, 'Unknown'),
            'file_size': file_stat.st_size,
            'cover_art_path': None,
        }
    
    def _parse_number(self, value) -> Optional[int]:
        """Parse a number from tag value (handles '1/12' format)."""
        if value is None:
            return None
        try:
            # Handle "track/total" format
            if isinstance(value, str) and '/' in value:
                value = value.split('/')[0]
            return int(value)
        except (ValueError, TypeError):
            return None
    
    def _extract_cover_art(self, file_path: str) -> Optional[str]:
        """Extract cover art from audio file and save to disk."""
        try:
            ext = Path(file_path).suffix.lower()
            image_data = None
            image_format = 'jpg'
            
            if ext == '.mp3':
                image_data, image_format = self._extract_mp3_cover(file_path)
            elif ext == '.flac':
                image_data, image_format = self._extract_flac_cover(file_path)
            elif ext in ('.m4a', '.mp4', '.aac'):
                image_data, image_format = self._extract_mp4_cover(file_path)
            elif ext == '.ogg':
                image_data, image_format = self._extract_ogg_cover(file_path)
            
            if image_data:
                # Create unique filename based on image hash
                image_hash = hashlib.md5(image_data).hexdigest()[:16]
                cover_filename = f"{image_hash}.{image_format}"
                cover_path = self.cover_art_dir / cover_filename
                
                if not cover_path.exists():
                    with open(cover_path, 'wb') as f:
                        f.write(image_data)
                
                return str(cover_path)
            
            # Check for cover art in same directory
            return self._find_folder_art(file_path)
            
        except Exception as e:
            print(f"Error extracting cover art: {e}")
            return self._find_folder_art(file_path)
    
    def _extract_mp3_cover(self, file_path: str) -> Tuple[Optional[bytes], str]:
        """Extract cover art from MP3 file."""
        try:
            audio = MP3(file_path)
            if audio.tags:
                for tag in audio.tags.values():
                    if isinstance(tag, APIC):
                        mime = tag.mime.lower()
                        fmt = 'png' if 'png' in mime else 'jpg'
                        return tag.data, fmt
        except Exception:
            pass
        return None, 'jpg'
    
    def _extract_flac_cover(self, file_path: str) -> Tuple[Optional[bytes], str]:
        """Extract cover art from FLAC file."""
        try:
            audio = FLAC(file_path)
            if audio.pictures:
                pic = audio.pictures[0]
                fmt = 'png' if 'png' in pic.mime.lower() else 'jpg'
                return pic.data, fmt
        except Exception:
            pass
        return None, 'jpg'
    
    def _extract_mp4_cover(self, file_path: str) -> Tuple[Optional[bytes], str]:
        """Extract cover art from M4A/MP4 file."""
        try:
            audio = MP4(file_path)
            if 'covr' in audio.tags:
                cover = audio.tags['covr'][0]
                # MP4 cover format: 13=JPEG, 14=PNG
                fmt = 'png' if cover.imageformat == 14 else 'jpg'
                return bytes(cover), fmt
        except Exception:
            pass
        return None, 'jpg'
    
    def _extract_ogg_cover(self, file_path: str) -> Tuple[Optional[bytes], str]:
        """Extract cover art from OGG file."""
        try:
            audio = OggVorbis(file_path)
            if 'metadata_block_picture' in audio:
                import base64
                data = base64.b64decode(audio['metadata_block_picture'][0])
                # Parse FLAC picture block
                # Skip: type(4) + mime_len(4) + mime + desc_len(4) + desc + w(4) + h(4) + d(4) + c(4) + data_len(4)
                offset = 4
                mime_len = struct.unpack('>I', data[offset:offset+4])[0]
                offset += 4 + mime_len
                desc_len = struct.unpack('>I', data[offset:offset+4])[0]
                offset += 4 + desc_len + 16  # Skip dimensions
                data_len = struct.unpack('>I', data[offset:offset+4])[0]
                offset += 4
                image_data = data[offset:offset+data_len]
                return image_data, 'jpg'
        except Exception:
            pass
        return None, 'jpg'
    
    def _find_folder_art(self, file_path: str) -> Optional[str]:
        """Look for cover art image in the same folder."""
        folder = Path(file_path).parent
        cover_names = [
            'cover', 'folder', 'album', 'front', 'artwork', 
            'Cover', 'Folder', 'Album', 'Front', 'Artwork'
        ]
        extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        
        for name in cover_names:
            for ext in extensions:
                cover_path = folder / f"{name}{ext}"
                if cover_path.exists():
                    return str(cover_path)
        
        # Check for any image file
        for ext in extensions:
            images = list(folder.glob(f"*{ext}"))
            if images:
                return str(images[0])
        
        return None


class MetadataWriter:
    """Writes metadata to audio files."""
    
    def __init__(self):
        if not MUTAGEN_AVAILABLE:
            raise ImportError("mutagen library is required. Install with: pip install mutagen")
    
    def write_metadata(self, file_path: str, metadata: Dict) -> bool:
        """Write metadata to an audio file."""
        if not os.path.exists(file_path):
            return False
        
        try:
            ext = Path(file_path).suffix.lower()
            
            if ext == '.mp3':
                return self._write_mp3_metadata(file_path, metadata)
            elif ext == '.flac':
                return self._write_flac_metadata(file_path, metadata)
            elif ext in ('.m4a', '.mp4', '.aac'):
                return self._write_mp4_metadata(file_path, metadata)
            elif ext == '.ogg':
                return self._write_ogg_metadata(file_path, metadata)
            else:
                # Try generic mutagen approach
                return self._write_generic_metadata(file_path, metadata)
                
        except Exception as e:
            print(f"Error writing metadata to {file_path}: {e}")
            return False
    
    def _write_mp3_metadata(self, file_path: str, metadata: Dict) -> bool:
        """Write metadata to MP3 file."""
        try:
            audio = MP3(file_path)
            if audio.tags is None:
                audio.add_tags()
            
            tag_mapping = {
                'title': TIT2,
                'artist': TPE1,
                'album': TALB,
                'album_artist': TPE2,
                'genre': TCON,
            }
            
            for key, tag_class in tag_mapping.items():
                if key in metadata and metadata[key]:
                    audio.tags.add(tag_class(encoding=3, text=str(metadata[key])))
            
            if 'year' in metadata and metadata['year']:
                audio.tags.add(TDRC(encoding=3, text=str(metadata['year'])))
            
            if 'track_number' in metadata and metadata['track_number']:
                audio.tags.add(TRCK(encoding=3, text=str(metadata['track_number'])))
            
            if 'disc_number' in metadata and metadata['disc_number']:
                audio.tags.add(TPOS(encoding=3, text=str(metadata['disc_number'])))
            
            audio.save()
            return True
            
        except Exception as e:
            print(f"Error writing MP3 tags: {e}")
            return False
    
    def _write_flac_metadata(self, file_path: str, metadata: Dict) -> bool:
        """Write metadata to FLAC file."""
        try:
            audio = FLAC(file_path)
            
            tag_mapping = {
                'title': 'title',
                'artist': 'artist',
                'album': 'album',
                'album_artist': 'albumartist',
                'genre': 'genre',
                'year': 'date',
                'track_number': 'tracknumber',
                'disc_number': 'discnumber',
            }
            
            for key, tag_name in tag_mapping.items():
                if key in metadata and metadata[key] is not None:
                    audio[tag_name] = str(metadata[key])
            
            audio.save()
            return True
            
        except Exception as e:
            print(f"Error writing FLAC tags: {e}")
            return False
    
    def _write_mp4_metadata(self, file_path: str, metadata: Dict) -> bool:
        """Write metadata to M4A/MP4 file."""
        try:
            audio = MP4(file_path)
            
            tag_mapping = {
                'title': '\xa9nam',
                'artist': '\xa9ART',
                'album': '\xa9alb',
                'album_artist': 'aART',
                'genre': '\xa9gen',
                'year': '\xa9day',
            }
            
            for key, tag_name in tag_mapping.items():
                if key in metadata and metadata[key] is not None:
                    audio[tag_name] = str(metadata[key])
            
            if 'track_number' in metadata and metadata['track_number']:
                audio['trkn'] = [(int(metadata['track_number']), 0)]
            
            if 'disc_number' in metadata and metadata['disc_number']:
                audio['disk'] = [(int(metadata['disc_number']), 0)]
            
            audio.save()
            return True
            
        except Exception as e:
            print(f"Error writing MP4 tags: {e}")
            return False
    
    def _write_ogg_metadata(self, file_path: str, metadata: Dict) -> bool:
        """Write metadata to OGG file."""
        try:
            audio = OggVorbis(file_path)
            
            tag_mapping = {
                'title': 'title',
                'artist': 'artist',
                'album': 'album',
                'album_artist': 'albumartist',
                'genre': 'genre',
                'year': 'date',
                'track_number': 'tracknumber',
                'disc_number': 'discnumber',
            }
            
            for key, tag_name in tag_mapping.items():
                if key in metadata and metadata[key] is not None:
                    audio[tag_name] = str(metadata[key])
            
            audio.save()
            return True
            
        except Exception as e:
            print(f"Error writing OGG tags: {e}")
            return False
    
    def _write_generic_metadata(self, file_path: str, metadata: Dict) -> bool:
        """Try to write metadata using mutagen's easy mode."""
        try:
            audio = MutagenFile(file_path, easy=True)
            if audio is None:
                return False
            
            tag_mapping = {
                'title': 'title',
                'artist': 'artist',
                'album': 'album',
                'album_artist': 'albumartist',
                'genre': 'genre',
                'year': 'date',
                'track_number': 'tracknumber',
                'disc_number': 'discnumber',
            }
            
            for key, tag_name in tag_mapping.items():
                if key in metadata and metadata[key] is not None:
                    audio[tag_name] = str(metadata[key])
            
            audio.save()
            return True
            
        except Exception as e:
            print(f"Error writing generic tags: {e}")
            return False
    
    def set_cover_art(self, file_path: str, image_path: str) -> bool:
        """Set cover art for an audio file."""
        if not os.path.exists(file_path) or not os.path.exists(image_path):
            return False
        
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Detect image type
            mime_type = 'image/jpeg'
            if image_path.lower().endswith('.png'):
                mime_type = 'image/png'
            
            ext = Path(file_path).suffix.lower()
            
            if ext == '.mp3':
                return self._set_mp3_cover(file_path, image_data, mime_type)
            elif ext == '.flac':
                return self._set_flac_cover(file_path, image_data, mime_type)
            elif ext in ('.m4a', '.mp4', '.aac'):
                return self._set_mp4_cover(file_path, image_data, mime_type)
            
            return False
            
        except Exception as e:
            print(f"Error setting cover art: {e}")
            return False
    
    def _set_mp3_cover(self, file_path: str, image_data: bytes, mime_type: str) -> bool:
        """Set cover art for MP3 file."""
        try:
            audio = MP3(file_path)
            if audio.tags is None:
                audio.add_tags()
            
            # Remove existing covers
            audio.tags.delall('APIC')
            
            # Add new cover
            audio.tags.add(APIC(
                encoding=3,
                mime=mime_type,
                type=3,  # Front cover
                desc='Cover',
                data=image_data
            ))
            
            audio.save()
            return True
        except Exception as e:
            print(f"Error setting MP3 cover: {e}")
            return False
    
    def _set_flac_cover(self, file_path: str, image_data: bytes, mime_type: str) -> bool:
        """Set cover art for FLAC file."""
        try:
            from mutagen.flac import Picture
            
            audio = FLAC(file_path)
            
            # Remove existing pictures
            audio.clear_pictures()
            
            # Add new picture
            picture = Picture()
            picture.type = 3  # Front cover
            picture.mime = mime_type
            picture.desc = 'Cover'
            picture.data = image_data
            
            audio.add_picture(picture)
            audio.save()
            return True
        except Exception as e:
            print(f"Error setting FLAC cover: {e}")
            return False
    
    def _set_mp4_cover(self, file_path: str, image_data: bytes, mime_type: str) -> bool:
        """Set cover art for M4A/MP4 file."""
        try:
            from mutagen.mp4 import MP4Cover
            
            audio = MP4(file_path)
            
            # Determine format
            fmt = MP4Cover.FORMAT_PNG if 'png' in mime_type else MP4Cover.FORMAT_JPEG
            
            audio['covr'] = [MP4Cover(image_data, imageformat=fmt)]
            audio.save()
            return True
        except Exception as e:
            print(f"Error setting MP4 cover: {e}")
            return False


class LibraryScanner:
    """Scans directories for audio files."""
    
    def __init__(self):
        self.metadata_reader = MetadataReader()
    
    def scan_directory(self, directory: str, recursive: bool = True) -> List[Dict]:
        """Scan a directory for audio files and return their metadata."""
        directory = Path(directory)
        if not directory.exists():
            return []
        
        tracks = []
        
        if recursive:
            pattern = '**/*'
        else:
            pattern = '*'
        
        for file_path in directory.glob(pattern):
            if file_path.is_file() and self.metadata_reader.is_supported(str(file_path)):
                metadata = self.metadata_reader.read_metadata(str(file_path))
                if metadata:
                    tracks.append(metadata)
        
        return tracks
    
    def get_supported_extensions(self) -> List[str]:
        """Return list of supported file extensions."""
        return list(SUPPORTED_FORMATS.keys())
