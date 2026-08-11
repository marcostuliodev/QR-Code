from typing import Optional
import os
from PIL import Image, ImageDraw
import qrcode
from qrcode import constants

ERROR_MAP = {
    'L': constants.ERROR_CORRECT_L,
    'M': constants.ERROR_CORRECT_M,
    'Q': constants.ERROR_CORRECT_Q,
    'H': constants.ERROR_CORRECT_H,
}


def _ensure_color(col: Optional[str]) -> str:
    if not col:
        return '#000000'
    return col


def generate_qr(
    data: str,
    output_path: str = 'qrcode.png',
    version: Optional[int] = None,
    error: str = 'M',
    box_size: int = 10,
    border: int = 4,
    module_color: str = '#000000',
    background: str = '#ffffff',
    module_shape: str = 'square',
    eye_color: Optional[str] = None,
    frame_path: Optional[str] = None,
    icon_path: Optional[str] = None,
    icon_size_ratio: float = 0.20,
    icon_border: int = 6,
):
    error_const = ERROR_MAP.get(error.upper(), constants.ERROR_CORRECT_M)

    qr = qrcode.QRCode(
        version=version,
        error_correction=error_const,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)

    matrix = qr.get_matrix()
    modules_count = len(matrix)
    img_size = (modules_count + 2 * border) * box_size

    img = Image.new('RGBA', (img_size, img_size), _ensure_color(background))
    draw = ImageDraw.Draw(img)

    for r in range(modules_count):
        for c in range(modules_count):
            if matrix[r][c]:
                x0 = (c + border) * box_size
                y0 = (r + border) * box_size
                x1 = x0 + box_size
                y1 = y0 + box_size
                if module_shape == 'circle':
                    draw.ellipse((x0, y0, x1, y1), fill=module_color)
                else:
                    draw.rectangle((x0, y0, x1, y1), fill=module_color)

    if eye_color:
        finder_size = 7
        positions = [
            (0, 0),
            (modules_count - finder_size, 0),
            (0, modules_count - finder_size),
        ]
        for (c0, r0) in positions:
            for r in range(r0, r0 + finder_size):
                for c in range(c0, c0 + finder_size):
                    if matrix[r][c]:
                        x0 = (c + border) * box_size
                        y0 = (r + border) * box_size
                        x1 = x0 + box_size
                        y1 = y0 + box_size
                        if module_shape == 'circle':
                            draw.ellipse((x0, y0, x1, y1), fill=eye_color)
                        else:
                            draw.rectangle((x0, y0, x1, y1), fill=eye_color)

    if frame_path and os.path.exists(frame_path):
        try:
            frame = Image.open(frame_path).convert('RGBA')
            frame = frame.resize((img_size, img_size), Image.LANCZOS)
            img = Image.alpha_composite(img, frame)
        except Exception:
            pass

    if icon_path and os.path.exists(icon_path):
        try:
            icon = Image.open(icon_path).convert('RGBA')
            w = int(img_size * icon_size_ratio)
            h = int(w * icon.size[1] / icon.size[0])
            icon = icon.resize((w, h), Image.LANCZOS)
            mask = icon.split()[3]
            if icon_border > 0:
                border_size = icon_border
                chip_w = w + border_size * 2
                chip_h = h + border_size * 2
                chip = Image.new('RGBA', (chip_w, chip_h), (255, 255, 255, 0))
                radius = min(border_size * 3, chip_w // 2, chip_h // 2)
                chip_draw = ImageDraw.Draw(chip)
                chip_draw.rounded_rectangle(
                    (0, 0, chip_w - 1, chip_h - 1), radius=radius, fill=(255, 255, 255, 255)
                )
                chip.paste(icon, (border_size, border_size), mask)
                icon = chip
                mask = icon.split()[3]
            pos = ((img_size - icon.size[0]) // 2, (img_size - icon.size[1]) // 2)
            img.paste(icon, pos, mask)
        except Exception:
            pass

    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    if output_path.lower().endswith(('.jpg', '.jpeg')):
        img = img.convert('RGB')

    img.save(output_path)


if __name__ == '__main__':
    print('Use web_app.py para iniciar o servidor Web.')
