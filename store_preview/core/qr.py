"""Small QR helpers for sharing app entry points without exposing PINs."""

import base64
from io import BytesIO

import qrcode


def data_url(value):
    image = qrcode.make(str(value))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
