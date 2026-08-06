import os
import tempfile
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from typing import Optional
from qr_studio import generate_qr

app = FastAPI()
app.mount('/static', StaticFiles(directory='.'), name='static')


@app.get('/', response_class=HTMLResponse)
def home():
    return FileResponse('index.html')


@app.post('/api/generate')
async def api_generate(
    data: str = Form(...),
    error: str = Form('M'),
    box_size: int = Form(10),
    border: int = Form(4),
    module_color: str = Form('#000000'),
    bg_color: str = Form('#ffffff'),
    shape: str = Form('square'),
    eye_color: Optional[str] = Form(None),
    icon: Optional[UploadFile] = File(None),
    frame: Optional[UploadFile] = File(None),
    icon_size: int = Form(20),
    icon_border: int = Form(6),
):
    tmp_icon = None
    tmp_frame = None
    out_tmp = None

    try:
        if icon is not None:
            suffix = os.path.splitext(icon.filename)[1] or '.png'
            tmp_icon_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp_icon_file.write(await icon.read())
            tmp_icon_file.close()
            tmp_icon = tmp_icon_file.name

        if frame is not None:
            suffix = os.path.splitext(frame.filename)[1] or '.png'
            tmp_frame_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp_frame_file.write(await frame.read())
            tmp_frame_file.close()
            tmp_frame = tmp_frame_file.name

        out_tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        out_tmp.close()

        generate_qr(
            data=data,
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

        return Response(content=content, media_type='image/png')
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        for path in (tmp_icon, tmp_frame, out_tmp.name if out_tmp is not None else None):
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except Exception:
                    pass
