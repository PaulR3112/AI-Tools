"""Rozdelenie dokumentu na PNG stránky (150–200 DPI)."""

import io

import pypdfium2 as pdfium

# Claude vision: dlhšia strana nad ~1568 px sa aj tak zmenšuje; väčší obrázok = zbytočné tokeny
MAX_LONG_SIDE_PX = 2000


def render_pages(data: bytes, content_type: str, dpi: int = 170) -> list[bytes]:
    if content_type == "application/pdf" or data[:5] == b"%PDF-":
        return _render_pdf(data, dpi)
    if content_type in ("image/png", "image/jpeg", "image/webp"):
        return [_image_to_png(data)]
    raise ValueError(f"Nepodporovaný typ dokumentu: {content_type}")


def _render_pdf(data: bytes, dpi: int) -> list[bytes]:
    pdf = pdfium.PdfDocument(data)
    try:
        pages: list[bytes] = []
        for page in pdf:
            w, h = page.get_size()  # v bodoch (1/72 palca)
            scale = min(dpi / 72, MAX_LONG_SIDE_PX / max(w, h))
            image = page.render(scale=scale).to_pil()
            buf = io.BytesIO()
            image.save(buf, format="PNG", optimize=True)
            pages.append(buf.getvalue())
            page.close()
        return pages
    finally:
        pdf.close()


def _image_to_png(data: bytes) -> bytes:
    from PIL import Image

    image = Image.open(io.BytesIO(data))
    image.thumbnail((MAX_LONG_SIDE_PX, MAX_LONG_SIDE_PX))
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()
