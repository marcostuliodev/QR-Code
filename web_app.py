import os
import re
import tempfile
from urllib.parse import quote
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from typing import Optional
from qr_studio import generate_qr

app = FastAPI()
app.mount('/static', StaticFiles(directory='.'), name='static')
app.mount('/assets', StaticFiles(directory='assets'), name='assets')


@app.middleware('http')
async def add_cache_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith('/assets/'):
        response.headers['Cache-Control'] = 'public, max-age=2592000, immutable'
    return response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR = os.path.join(BASE_DIR, 'assets', 'icons')


def _clean_digits(value: str) -> str:
    return re.sub(r'\D', '', value or '')


def _clean_username(value: str) -> str:
    return (value or '').strip().strip('@').strip()


def _normalize_url(value: str) -> str:
    url = (value or '').strip()
    if not url:
        raise ValueError('Informe o link.')
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url


def _escape_wifi(value: str) -> str:
    return value.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('"', '\\"').replace(':', '\\:')


_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
_UUID_RE = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
_PIX_MERCHANT_NAME = 'PIX'
_PIX_MERCHANT_CITY = 'BR'


def _crc16_ccitt(data: str) -> str:
    crc = 0xFFFF
    for byte in data.encode('utf-8'):
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return f'{crc:04X}'


def _emv_field(fid: str, value: str) -> str:
    return f'{fid}{len(value):02d}{value}'


def _normalize_pix_key(value: str) -> str:
    key = (value or '').strip()
    if not key:
        raise ValueError('Informe a chave Pix.')
    if '@' in key:
        key = key.lower()
        if not _EMAIL_RE.match(key) or len(key) > 77:
            raise ValueError('Chave Pix de e-mail inválida.')
        return key
    if _UUID_RE.match(key):
        return key.lower()
    if key.startswith('+'):
        digits = re.sub(r'\D', '', key)
        if not digits:
            raise ValueError('Chave Pix de telefone inválida.')
        if re.fullmatch(r'[1-9][0-9]{1,14}', digits):
            return '+' + digits
        raise ValueError('Chave Pix de telefone inválida. Use o formato +55DDDNÚMERO.')
    compact = re.sub(r'[.\-/\s()]', '', key)
    if re.fullmatch(r'[0-9]{11}', compact):
        return compact
    if re.fullmatch(r'[a-z0-9]{14}', compact, re.IGNORECASE):
        return compact
    if re.fullmatch(r'55[0-9]{10,11}', compact):
        return '+' + compact
    raise ValueError('Chave Pix inválida. Use e-mail, CPF, CNPJ, telefone (+55...) ou chave aleatória.')


def build_pix_payload(pix_key: str) -> str:
    key = _normalize_pix_key(pix_key)
    merchant_info = _emv_field('00', 'br.gov.bcb.pix') + _emv_field('01', key)
    payload = (
        _emv_field('00', '01')
        + _emv_field('26', merchant_info)
        + _emv_field('52', '0000')
        + _emv_field('53', '986')
        + _emv_field('58', 'BR')
        + _emv_field('59', _PIX_MERCHANT_NAME)
        + _emv_field('60', _PIX_MERCHANT_CITY)
        + _emv_field('62', _emv_field('05', '***'))
    )
    return payload + '6304' + _crc16_ccitt(payload + '6304')


def format_qr_data(qr_type: str, fields: dict) -> str:
    t = (qr_type or 'text').lower()

    if t == 'link':
        return _normalize_url(fields.get('url'))

    if t == 'whatsapp':
        number = _clean_digits(fields.get('whatsapp'))
        if not number:
            raise ValueError('Informe o número do WhatsApp.')
        return f'https://wa.me/{number}'

    if t == 'instagram':
        user = _clean_username(fields.get('instagram'))
        if not user:
            raise ValueError('Informe o usuário do Instagram.')
        return f'https://instagram.com/{user}'

    if t == 'tiktok':
        user = _clean_username(fields.get('tiktok'))
        if not user:
            raise ValueError('Informe o usuário do TikTok.')
        return f'https://www.tiktok.com/@{user}'

    if t == 'x':
        user = _clean_username(fields.get('x'))
        if not user:
            raise ValueError('Informe o usuário do X (Twitter).')
        return f'https://x.com/{user}'

    if t == 'telegram':
        user = _clean_username(fields.get('telegram'))
        if not user:
            raise ValueError('Informe o usuário do Telegram.')
        return f'https://t.me/{user}'

    if t in ('youtube', 'facebook', 'linkedin'):
        return _normalize_url(fields.get(t))

    if t == 'email':
        address = (fields.get('email') or '').strip()
        if not address:
            raise ValueError('Informe o e-mail.')
        subject = (fields.get('email_subject') or '').strip()
        body = (fields.get('email_body') or '').strip()
        parts = []
        if subject:
            parts.append('subject=' + quote(subject))
        if body:
            parts.append('body=' + quote(body))
        return 'mailto:' + address + ('?' + '&'.join(parts) if parts else '')

    if t == 'phone':
        number = _clean_digits(fields.get('phone'))
        if not number:
            raise ValueError('Informe o número de telefone.')
        return f'tel:+{number}'

    if t == 'pix':
        return build_pix_payload(fields.get('pix_key'))

    if t == 'wifi':
        ssid = (fields.get('wifi_ssid') or '').strip()
        if not ssid:
            raise ValueError('Informe o nome da rede Wi-Fi.')
        password = (fields.get('wifi_password') or '').strip()
        security = (fields.get('wifi_security') or 'WPA').upper()
        hidden = (fields.get('wifi_hidden') or '').lower() in ('true', 'on', '1')
        if security not in ('WPA', 'WEP', 'NOPASS'):
            security = 'WPA'
        if security == 'NOPASS':
            return f"WIFI:T:nopass;S:{_escape_wifi(ssid)};;"
        if not password:
            raise ValueError('Informe a senha da rede Wi-Fi.')
        parts = [f'WIFI:T:{security}', f'S:{_escape_wifi(ssid)}', f'P:{_escape_wifi(password)}']
        if hidden:
            parts.append('H:true')
        return ';'.join(parts) + ';;'

    text = (fields.get('text') or fields.get('data') or '').strip()
    if not text:
        raise ValueError('Informe o texto.')
    return text


@app.get('/', response_class=HTMLResponse)
def home():
    return FileResponse('index.html')


@app.post('/api/generate')
async def api_generate(
    data: str = Form(''),
    qr_type: str = Form('text'),
    url: str = Form(''),
    whatsapp: str = Form(''),
    instagram: str = Form(''),
    tiktok: str = Form(''),
    x: str = Form(''),
    telegram: str = Form(''),
    youtube: str = Form(''),
    facebook: str = Form(''),
    linkedin: str = Form(''),
    email: str = Form(''),
    email_subject: str = Form(''),
    email_body: str = Form(''),
    phone: str = Form(''),
    pix_key: str = Form(''),
    wifi_ssid: str = Form(''),
    wifi_password: str = Form(''),
    wifi_security: str = Form('WPA'),
    wifi_hidden: str = Form('false'),
    text: str = Form(''),
    error: str = Form('M'),
    box_size: int = Form(10),
    border: int = Form(4),
    module_color: str = Form('#000000'),
    bg_color: str = Form('#ffffff'),
    shape: str = Form('square'),
    eye_color: Optional[str] = Form(None),
    icon: Optional[UploadFile] = File(None),
    frame: Optional[UploadFile] = File(None),
    icon_preset: str = Form(''),
    icon_size: int = Form(20),
    icon_border: int = Form(6),
):
    tmp_icon = None
    tmp_frame = None
    out_tmp = None

    try:
        fields = {
            'url': url,
            'whatsapp': whatsapp,
            'instagram': instagram,
            'tiktok': tiktok,
            'x': x,
            'telegram': telegram,
            'youtube': youtube,
            'facebook': facebook,
            'linkedin': linkedin,
            'email': email,
            'email_subject': email_subject,
            'email_body': email_body,
            'phone': phone,
            'pix_key': pix_key,
            'wifi_ssid': wifi_ssid,
            'wifi_password': wifi_password,
            'wifi_security': wifi_security,
            'wifi_hidden': wifi_hidden,
            'text': text,
            'data': data,
        }
        if data.strip():
            final_data = data.strip()
        else:
            final_data = format_qr_data(qr_type, fields)

        if icon is not None:
            suffix = os.path.splitext(icon.filename)[1] or '.png'
            tmp_icon_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp_icon_file.write(await icon.read())
            tmp_icon_file.close()
            tmp_icon = tmp_icon_file.name
        elif icon_preset:
            preset_path = os.path.join(ICONS_DIR, f'{icon_preset}.png')
            if os.path.exists(preset_path):
                tmp_icon = preset_path

        if frame is not None:
            suffix = os.path.splitext(frame.filename)[1] or '.png'
            tmp_frame_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp_frame_file.write(await frame.read())
            tmp_frame_file.close()
            tmp_frame = tmp_frame_file.name

        out_tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        out_tmp.close()

        generate_qr(
            data=final_data,
            output_path=out_tmp.name,
            error=error,
            box_size=box_size,
            border=border,
            module_color=module_color,
            background=bg_color,
            module_shape=shape,
            eye_color=eye_color,
            frame_path=tmp_frame,
            icon_path=tmp_icon,
            icon_size_ratio=(icon_size / 100.0),
            icon_border=icon_border,
        )

        with open(out_tmp.name, 'rb') as f:
            content = f.read()

        return Response(
            content=content,
            media_type='image/png',
            headers={'X-QR-Data': quote(final_data)},
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if tmp_icon and os.path.exists(tmp_icon) and not tmp_icon.startswith(ICONS_DIR):
            try:
                os.unlink(tmp_icon)
            except Exception:
                pass
        if tmp_frame and os.path.exists(tmp_frame):
            try:
                os.unlink(tmp_frame)
            except Exception:
                pass
        if out_tmp is not None and os.path.exists(out_tmp.name):
            try:
                os.unlink(out_tmp.name)
            except Exception:
                pass
