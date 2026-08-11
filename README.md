# QR Studio

Gerador de QR Codes simples e profissional. Escolha o tipo de conteúdo, informe apenas o que importa e o gerador monta a formatação correta automaticamente — com pré-visualização ao vivo, ícones de marca e download em PNG.

## Funcionalidades

- **Tipos de QR Code**: Link, WhatsApp, Instagram, TikTok, X (Twitter), Telegram, YouTube, Facebook, LinkedIn, E-mail, Telefone, Wi-Fi e Texto.
- **Campos inteligentes**:
  - WhatsApp → só o número (DDI incluído, ex.: `5511999999999`)
  - Instagram/TikTok/X/Telegram → só o nome de usuário
  - Wi-Fi → nome da rede (SSID), senha, segurança e rede oculta; a formatação `WIFI:T:...` é gerada sozinha
  - E-mail → endereço com assunto e mensagem opcionais
- **Ícone central**: 14 ícones de marca/genericos prontos ou upload do seu logo (PNG), com chip branco arredondado.
- **Personalização**: cor dos módulos, fundo e olhos, formato quadrado/círculo, correção de erro, tamanho do módulo e borda.
- **Pré-visualização ao vivo** com atualização automática (debounce) e botão manual **Gerar QR Code**.
- **Download em PNG** com nome de arquivo personalizável.
- **Resiliente**: se a API não estiver disponível (ex.: abrir o `index.html` direto no navegador), o QR é gerado **no próprio navegador** via Canvas, mantendo o download funcionando.

## Tecnologias

- **Backend**: Python, FastAPI, `qrcode[pil]` + Pillow
- **Frontend**: HTML/CSS/JS puros (sem framework), ícones SVG inline (Lucide + Simple Icons)
- **Deploy**: Vercel (runtime Python via `pyproject.toml` + `uv`)

## Como executar localmente

Pré-requisitos: Python 3.11+.

```bash
# 1. Criar e ativar o ambiente virtual (opcional, recomendado)
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/macOS

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Subir o servidor
uvicorn web_app:app --reload
```

Abra [http://127.0.0.1:8000](http://127.0.0.1:8000).

> **Sem o servidor?** Você ainda pode abrir o `index.html` diretamente no navegador
> (duplo clique): o QR Code será gerado client-side. Para o modo completo
> (ícones de marca e estilos avançados servidos pelo backend), use o servidor.

## Deploy no Vercel

O projeto usa o runtime Python moderno da Vercel, detectado via `pyproject.toml` + `uv.lock`. Basta conectar o repositório na Vercel — não é preciso configurar nada manualmente:

- Entrada: `main:app`, definida em `[tool.vercel] entrypoint` no `pyproject.toml`.
- Build: a Vercel roda `uv sync --locked` a partir do `uv.lock` (já incluído no repositório).
- `[tool.uv] package = false` informa que o projeto é uma aplicação (não um pacote Python), evitando o build de wheel.

Para atualizar o lockfile após mudar dependências: `uv lock`.

## API

### `POST /api/generate`

Gera o QR Code e retorna a imagem PNG.

**Parâmetros (multipart/form-data)**

| Parâmetro | Descrição |
| --- | --- |
| `qr_type` | `link`, `whatsapp`, `instagram`, `tiktok`, `x`, `telegram`, `youtube`, `facebook`, `linkedin`, `email`, `phone`, `wifi` ou `text` (padrão: `text`) |
| `url` / `whatsapp` / `instagram` / `tiktok` / `x` / `telegram` / `youtube` / `facebook` / `linkedin` | Valor principal de cada tipo |
| `email`, `email_subject`, `email_body` | E-mail com assunto/mensagem opcionais |
| `phone` | Número para `tel:` |
| `wifi_ssid`, `wifi_password`, `wifi_security` (`WPA`/`WEP`/`NOPASS`), `wifi_hidden` | Rede Wi-Fi |
| `text` | Texto livre |
| `error` | `L`, `M`, `Q` ou `H` (padrão `M`) |
| `box_size`, `border` | Tamanho do módulo e borda (padrões 10 e 4) |
| `module_color`, `bg_color`, `eye_color` | Cores em HEX |
| `shape` | `square` ou `circle` |
| `icon_preset` | Nome do ícone embutido (ex.: `whatsapp`, `instagram`, `wifi`, `globe`) |
| `icon`, `frame` | Upload de logo/moldura PNG (opcional) |
| `icon_size`, `icon_border` | Tamanho (%) e borda do ícone |

**Resposta**: `image/png` com o cabeçalho `X-QR-Data` contendo o conteúdo final (URL-encoded).

**Erros**: `400` com `detail` quando um campo obrigatório está vazio; `500` em falhas internas.

## Estrutura

```
├── index.html          # Frontend completo (single page)
├── web_app.py          # API FastAPI (rotas, formatação por tipo, uploads)
├── qr_studio.py        # Geração da imagem do QR (Pillow)
├── main.py             # Entrypoint do Vercel (main:app)
├── assets/
│   ├── icons.js        # Sprite SVG inline (ícones da interface)
│   ├── qrcode.min.js   # Lib QR client-side (fallback no navegador)
│   └── icons/          # PNGs dos ícones embutidos no QR
├── pyproject.toml      # Metadados + dependências (uv) + entrypoint Vercel
├── uv.lock             # Lockfile gerado por `uv lock`
├── requirements.txt    # Alternativa para pip
└── vercel.json
```

## Licença dos ícones

- **Lucide** — licença ISC
- **Simple Icons** — licença CC0 (domínio público)
- **qrcode-generator** — licença MIT
