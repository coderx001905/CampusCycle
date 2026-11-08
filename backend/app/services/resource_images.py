import io
import os
import re
import tempfile
import warnings
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import Settings

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_MULTIPART_OVERHEAD_BYTES = 64 * 1024
MAX_IMAGE_PIXELS = 12_000_000
MAX_IMAGE_DIMENSION = 6_000
_EXTENSIONS = {"JPEG": {".jpg", ".jpeg"}, "PNG": {".png"}, "WEBP": {".webp"}}
_MEDIA_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
_OUTPUT_EXTENSIONS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
_STORED_NAME = re.compile(r"^[0-9a-f]{32}\.(?:jpg|png|webp)$")


class ImageUploadError(ValueError):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class ProcessedImage:
    content: bytes
    extension: str
    media_type: str


def resource_image_root(settings: Settings) -> Path:
    configured = settings.resource_image_dir
    backend_root = Path(__file__).resolve().parents[2]
    root = (configured if configured.is_absolute() else backend_root / configured).resolve()
    return root


def process_uploaded_image(content: bytes, *, filename: str | None, content_type: str | None) -> ProcessedImage:
    if not content or len(content) > MAX_IMAGE_BYTES:
        raise ImageUploadError(413 if len(content) > MAX_IMAGE_BYTES else 422,
                               "Image must be non-empty and no larger than 5 MB.")
    if (not filename or "/" in filename or "\\" in filename or filename in {".", ".."}):
        raise ImageUploadError(422, "Provide a simple image filename with a supported extension.")
    extension = Path(filename).suffix.lower()
    allowed_format = next((fmt for fmt, extensions in _EXTENSIONS.items() if extension in extensions), None)
    if allowed_format is None or content_type != _MEDIA_TYPES[allowed_format]:
        raise ImageUploadError(415, "Only matching JPEG, PNG, or WebP image uploads are supported.")

    oriented: Image.Image | None = None
    clean: Image.Image | None = None
    rgba: Image.Image | None = None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as probe:
                actual_format = probe.format
                if actual_format != allowed_format or getattr(probe, "n_frames", 1) != 1:
                    raise ImageUploadError(415, "Image content does not match a supported single-frame raster format.")
                width, height = probe.size
                if (width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION or
                        width * height > MAX_IMAGE_PIXELS):
                    raise ImageUploadError(413, "Image dimensions exceed the safe processing limit.")
                probe.verify()
            with Image.open(io.BytesIO(content)) as decoded:
                decoded.load()
                oriented = ImageOps.exif_transpose(decoded)
                has_alpha = "A" in oriented.getbands() or "transparency" in oriented.info
                if actual_format == "JPEG":
                    rgba = oriented.convert("RGBA")
                    clean = Image.new("RGB", rgba.size, (255, 255, 255))
                    clean.paste(rgba, mask=rgba.getchannel("A"))
                    save_options = {"quality": 90, "optimize": True}
                else:
                    clean = oriented.convert("RGBA" if has_alpha else "RGB")
                    save_options = ({"optimize": True} if actual_format == "PNG"
                                    else {"quality": 90, "method": 4})
                output = io.BytesIO()
                clean.save(output, format=actual_format, **save_options)
                sanitized = output.getvalue()
    except ImageUploadError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as exc:
        raise ImageUploadError(422, "The uploaded image is malformed or too large to process safely.") from exc
    finally:
        for image in (rgba, clean, oriented):
            if image is not None:
                image.close()

    if len(sanitized) > MAX_IMAGE_BYTES:
        raise ImageUploadError(413, "Processed image exceeds the 5 MB storage limit.")
    return ProcessedImage(sanitized, _OUTPUT_EXTENSIONS[actual_format], _MEDIA_TYPES[actual_format])


def store_processed_image(processed: ProcessedImage, settings: Settings) -> str:
    root = resource_image_root(settings)
    temporary_path: Path | None = None
    try:
        root.mkdir(parents=True, exist_ok=True)
        stored_name = f"{uuid4().hex}.{processed.extension}"
        final_path = root / stored_name
        with tempfile.NamedTemporaryFile(mode="wb", prefix=".upload-", suffix=".tmp",
                                         dir=root, delete=False) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(processed.content)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, final_path)
        return stored_name
    except OSError as exc:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise ImageUploadError(500, "Image storage is unavailable.") from exc


def safe_stored_image_path(settings: Settings, reference: str | None) -> Path | None:
    if not reference or not _STORED_NAME.fullmatch(reference):
        return None
    root = resource_image_root(settings)
    candidate = root / reference
    try:
        if candidate.is_symlink() or candidate.resolve(strict=True).parent != root:
            return None
        if not candidate.is_file():
            return None
    except OSError:
        return None
    return candidate


def remove_stored_image(settings: Settings, reference: str | None) -> bool:
    if reference is None:
        return True
    path = safe_stored_image_path(settings, reference)
    if path is None:
        return False
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return True
    except OSError:
        return False
