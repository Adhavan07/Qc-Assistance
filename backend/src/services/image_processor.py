"""
Image Processing & PDF Page Rasterization Service.
Renders high-fidelity page images (150-300 DPI) and thumbnails,
handles format normalization, decompression defense, and OCR image preprocessing.
"""

import io
import os
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

try:
    import pypdfium2 as pdfium
    HAS_PDFIUM = True
except ImportError:
    HAS_PDFIUM = False


class ImageProcessor:
    """Handles rasterization of drawing documents (PDF/images) into displayable viewports and thumbnails."""

    MAX_PIXELS = 100_000_000  # 100 Megapixels decompression bomb protection
    MAX_DIMENSION = 10_000
    DEFAULT_DPI = 150
    THUMBNAIL_MAX_WIDTH = 320

    @classmethod
    def rasterize_document(
        cls,
        content: bytes,
        filename: str,
        mime_type: Optional[str] = None,
        dpi: int = DEFAULT_DPI,
    ) -> List[Dict[str, Any]]:
        """
        Rasterize a document (PDF or raster image) into page image bytes and thumbnails.
        Returns a list of dicts with:
        - page_number: int (1-indexed)
        - image_bytes: bytes (PNG format)
        - thumbnail_bytes: bytes (PNG format)
        - width: int (pixels)
        - height: int (pixels)
        """
        ext = os.path.splitext(filename.lower())[1]
        is_pdf = ext == ".pdf" or (mime_type == "application/pdf") or content.startswith(b"%PDF")

        if is_pdf:
            return cls.rasterize_pdf(content, dpi=dpi)
        elif ext in [".png", ".jpg", ".jpeg"] or (mime_type and mime_type.startswith("image/")):
            return [cls.process_raster_image(content)]
        else:
            raise ValueError(f"Unsupported document format: {ext}. Permitted formats: .pdf, .png, .jpg, .jpeg")

    @classmethod
    def rasterize_pdf(cls, pdf_bytes: bytes, dpi: int = DEFAULT_DPI) -> List[Dict[str, Any]]:
        """Rasterize each PDF page into high-resolution PNG image and thumbnail."""
        if not pdf_bytes:
            raise ValueError("PDF content is empty")

        if HAS_PDFIUM:
            try:
                return cls._rasterize_pdf_pdfium(pdf_bytes, dpi=dpi)
            except Exception:
                # If pdfium fails on corrupt stream, fall through to fallback
                pass

        return cls._rasterize_pdf_fallback(pdf_bytes, dpi=dpi)

    @classmethod
    def _rasterize_pdf_pdfium(cls, pdf_bytes: bytes, dpi: int = DEFAULT_DPI) -> List[Dict[str, Any]]:
        doc = pdfium.PdfDocument(pdf_bytes)
        try:
            scale = max(0.5, dpi / 72.0)
            pages: List[Dict[str, Any]] = []

            for idx in range(len(doc)):
                page = doc.get_page(idx)
                try:
                    bitmap = page.render(scale=scale)
                    pil_img = bitmap.to_pil()

                    # Ensure RGB
                    if pil_img.mode != "RGB":
                        pil_img = pil_img.convert("RGB")

                    width, height = pil_img.size

                    # Save full image PNG
                    full_buf = io.BytesIO()
                    pil_img.save(full_buf, format="PNG", optimize=True)
                    full_bytes = full_buf.getvalue()

                    # Generate thumbnail preserving aspect ratio
                    thumb_scale = min(1.0, cls.THUMBNAIL_MAX_WIDTH / max(1, width))
                    thumb_w = max(50, int(width * thumb_scale))
                    thumb_h = max(50, int(height * thumb_scale))
                    thumb_img = pil_img.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                    thumb_buf = io.BytesIO()
                    thumb_img.save(thumb_buf, format="PNG", optimize=True)
                    thumb_bytes = thumb_buf.getvalue()

                    pages.append({
                        "page_number": idx + 1,
                        "image_bytes": full_bytes,
                        "thumbnail_bytes": thumb_bytes,
                        "width": width,
                        "height": height,
                    })
                finally:
                    page.close()

            return pages
        finally:
            doc.close()

    @classmethod
    def _rasterize_pdf_fallback(cls, pdf_bytes: bytes, dpi: int = DEFAULT_DPI) -> List[Dict[str, Any]]:
        """Fallback renderer using pypdf text extraction and PIL synthetic rasterization."""
        import pypdf

        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        page_count = max(1, len(reader.pages))
        pages: List[Dict[str, Any]] = []

        for idx, page in enumerate(reader.pages, start=1):
            w = int(page.mediabox.width * (dpi / 72.0)) if page.mediabox else 1200
            h = int(page.mediabox.height * (dpi / 72.0)) if page.mediabox else 850
            w = min(cls.MAX_DIMENSION, max(400, w))
            h = min(cls.MAX_DIMENSION, max(400, h))

            # Create clean white engineering canvas
            canvas = Image.new("RGB", (w, h), color=(255, 255, 255))
            draw = ImageDraw.Draw(canvas)

            # Draw outer drawing border
            draw.rectangle([20, 20, w - 20, h - 20], outline=(180, 180, 180), width=2)
            draw.rectangle([25, 25, w - 25, h - 25], outline=(220, 220, 220), width=1)

            # Render extracted text onto canvas
            text = page.extract_text() or ""
            lines = [line.strip() for line in text.splitlines() if line.strip()][:40]
            y = 50
            for line in lines:
                draw.text((40, y), line[:100], fill=(30, 30, 30))
                y += 22
                if y > h - 60:
                    break

            # Save full image
            full_buf = io.BytesIO()
            canvas.save(full_buf, format="PNG")
            full_bytes = full_buf.getvalue()

            # Thumbnail
            thumb_scale = min(1.0, cls.THUMBNAIL_MAX_WIDTH / max(1, w))
            thumb_w = max(50, int(w * thumb_scale))
            thumb_h = max(50, int(h * thumb_scale))
            thumb_img = canvas.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
            thumb_buf = io.BytesIO()
            thumb_img.save(thumb_buf, format="PNG")
            thumb_bytes = thumb_buf.getvalue()

            pages.append({
                "page_number": idx,
                "image_bytes": full_bytes,
                "thumbnail_bytes": thumb_bytes,
                "width": w,
                "height": h,
            })

        return pages

    @classmethod
    def process_raster_image(cls, image_bytes: bytes) -> Dict[str, Any]:
        """Normalize, sanitize, and thumbnail a raster schematic image."""
        if not image_bytes:
            raise ValueError("Image content is empty")

        with Image.open(io.BytesIO(image_bytes)) as raw_img:
            # EXIF orientation normalization
            img = ImageOps.exif_transpose(raw_img) or raw_img

            w, h = img.size
            if (w * h) > cls.MAX_PIXELS or w > cls.MAX_DIMENSION or h > cls.MAX_DIMENSION:
                raise ValueError(
                    f"Image dimension ({w}x{h}) exceeds maximum safety limit "
                    f"(10,000 px / 100 MP decompression limit)."
                )

            # Convert to RGB if palette or CMYK or RGBA
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Save high-res PNG
            full_buf = io.BytesIO()
            img.save(full_buf, format="PNG", optimize=True)
            full_bytes = full_buf.getvalue()

            # Generate thumbnail
            thumb_scale = min(1.0, cls.THUMBNAIL_MAX_WIDTH / max(1, w))
            thumb_w = max(50, int(w * thumb_scale))
            thumb_h = max(50, int(h * thumb_scale))
            thumb_img = img.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
            thumb_buf = io.BytesIO()
            thumb_img.save(thumb_buf, format="PNG", optimize=True)
            thumb_bytes = thumb_buf.getvalue()

            return {
                "page_number": 1,
                "image_bytes": full_bytes,
                "thumbnail_bytes": thumb_bytes,
                "width": w,
                "height": h,
            }

    @classmethod
    def preprocess_for_ocr(cls, image: Image.Image) -> Image.Image:
        """Enhance contrast and binarize image for accurate OCR extraction."""
        gray = ImageOps.grayscale(image)
        contrasted = ImageOps.autocontrast(gray, cutoff=2)
        # Gentle unsharp mask to clarify wire line callouts
        sharpened = contrasted.filter(ImageFilter.UnsharpMask(radius=1.5, percent=130, threshold=3))
        return sharpened
