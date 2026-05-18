# =============================================================================
# 📦 IMPORTAÇÕES (As Ferramentas que o Python vai usar)
# =============================================================================

# FastAPI: O framework que cria o servidor web.
# Form: Permite que o servidor entenda dados enviados por formulários de sites.
from fastapi import FastAPI, Form

# HTMLResponse: Avisa ao navegador que o que vamos enviar é uma página visual (site).
from fastapi.responses import HTMLResponse

# Optional: Diz que uma variável pode ou não ter um valor (pode ser vazia).
from typing import Optional
from contextlib import asynccontextmanager

# os: Permite que o Python interaja com o sistema operacional (como pastas e portas).
import os

# Request: Representa a requisição HTTP bruta que chega ao servidor.
from fastapi import Request

# json: Ferramenta para ler e organizar dados no formato JSON (padrão de APIs).
import json

# Body: Força o FastAPI a esperar um conteúdo no corpo da mensagem (essencial para o /docs).
from fastapi import Body
import hmac
import hashlib

# Import do bot de despacho
from .bot_dispacho import executar_automacao

# Threading para executar o bot em paralelo
from threading import Thread
import asyncio
from playwright.async_api import async_playwright
from .bot_dispacho import fazer_login, URL_PEDIDOS

from fastapi import FastAPI

@app.get("/")
def home():
    return {"status": "ok"}
# =============================================================================
# 🚀 INICIALIZAÇÃO (Ligando os motores)
# =============================================================================
# Criamos o motor do bot em threads separadas para cada conta.
BOT_1_QUEUE = set()
BOT_2_QUEUE = set()

# Configuração dos dois bots
BOT_CONFIGS = {
    "Nipô": {
        "user_data_dir": "user_data_nipo",
        "email": "niposushidelivery@outlook.com",
        "senha": "Nipo4145!",
        "fila": BOT_1_QUEUE,
        "bot_name": "Nipô",
    },
    "Ene": {
        "user_data_dir": "user_data_ene",
        "email": "adm@niposushi.com.br",
        "senha": "Ene@sushi12",
        "fila": BOT_2_QUEUE,
        "bot_name": "Ene",
    },
}


# Inicializa a thread de cada bot com sua própria sessão de usuário.
def start_worker(user_data_dir, email, senha, fila_pedidos, bot_name):
    print(f"🚀 Iniciando o Trabalhador background do bot {bot_name}...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(
        executar_automacao(
            user_data_dir=user_data_dir,
            email=email,
            senha=senha,
            fila_pedidos=fila_pedidos,
            bot_name=bot_name,
        )
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ao iniciar a aplicação, dispara os dois workers do Playwright em background.
    Thread(
        target=start_worker,
        args=(
            BOT_CONFIGS["Nipô"]["user_data_dir"],
            BOT_CONFIGS["Nipô"]["email"],
            BOT_CONFIGS["Nipô"]["senha"],
            BOT_CONFIGS["Nipô"]["fila"],
            BOT_CONFIGS["Nipô"]["bot_name"],
        ),
        daemon=True,
    ).start()
    Thread(
        target=start_worker,
        args=(
            BOT_CONFIGS["Ene"]["user_data_dir"],
            BOT_CONFIGS["Ene"]["email"],
            BOT_CONFIGS["Ene"]["senha"],
            BOT_CONFIGS["Ene"]["fila"],
            BOT_CONFIGS["Ene"]["bot_name"],
        ),
        daemon=True,
    ).start()
    yield


app = FastAPI(lifespan=lifespan)


# =============================================================================
# 🧠 VARIÁVEL GLOBAL (A Memória do Servidor)
# =============================================================================
# 'numero_form' funciona como um post-it.
# Quando você digita no formulário, o valor é colado aqui para ser usado depois.
# Começa como None (vazio) porque o site acabou de ligar.
numero_form: Optional[str] = None
bot_selecionado: Optional[str] = None


# =============================================================================
# 🎨 FUNÇÃO DE LAYOUT (O Arquiteto do Site)
# =============================================================================
def layout(conteudo):
    return f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Zero48 Tech</title>

        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">

        <style>
        :root {{
            --primary: #00eaff;
            --secondary: #0066ff;
            --bg-dark: #020617;
            --card-bg: rgba(255, 255, 255, 0.06);
            --border: rgba(255, 255, 255, 0.15);
            --text: #ffffff;
            --text-dim: #94a3b8;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Outfit', sans-serif;
            background: linear-gradient(135deg, #1a3a52 0%, #0a1929 100%);
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            color: var(--text);
            padding: 20px;
        }}

        .container {{
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(40px) saturate(180%);
            -webkit-backdrop-filter: blur(40px) saturate(180%);
            width: 100%;
            max-width: 420px;
            padding: 40px;
            border-radius: 32px;
            border: 1px solid rgba(255, 255, 255, 0.18);
            box-shadow:
                0 25px 50px rgba(0,0,0,0.5),
                0 0 60px rgba(0, 234, 255, 0.1),
                inset 0 1px 0 rgba(255, 255, 255, 0.2);
            text-align: center;
            position: relative;
            overflow: hidden;
            animation: float 6s ease-in-out infinite;
        }}

        /* ESTILO ADICIONAL PARA O RADAR */
        .radar-section {{
            margin-bottom: 25px;
            border-bottom: 1px solid rgba(0,234,255,0.2);
            padding-bottom: 20px;
            text-align: left;
        }}
        
        .btn-mini {{
            background: rgba(0, 234, 255, 0.1);
            border: 1px solid var(--primary);
            color: var(--primary);
            padding: 5px 10px;
            border-radius: 8px;
            font-size: 0.7rem;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        
        .btn-mini:hover {{
            background: var(--primary);
            color: #000;
        }}

        .radar-container {{
            max-height: 150px;
            overflow-y: auto;
            margin-top: 10px;
            background: rgba(0,0,0,0.2);
            border-radius: 12px;
            padding: 8px;
        }}

        @keyframes float {{
            0%, 100% {{
                transform: translateY(0px);
            }}
            50% {{
                transform: translateY(-5px);
            }}
        }}

        .container::before {{
            content: "";
            position: absolute;
            inset: -3px;
            border-radius: 35px;
            background: linear-gradient(135deg,
                rgba(0, 234, 255, 0.15) 0%,
                rgba(100, 200, 255, 0.08) 25%,
                transparent 50%,
                rgba(0, 150, 220, 0.08) 75%,
                rgba(0, 234, 255, 0.15) 100%);
            z-index: -1;
            animation: borderGlow 8s ease-in-out infinite;
        }}

        .container::after {{
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 1px;
            background: linear-gradient(90deg,
                transparent 0%,
                rgba(255, 255, 255, 0.4) 50%,
                transparent 100%);
            z-index: 1;
        }}

        @keyframes borderGlow {{
            0%, 100% {{
                opacity: 0.6;
                transform: scale(1);
            }}
            50% {{
                opacity: 1;
                transform: scale(1.02);
            }}
        }}

        .logo {{
            font-weight: 800;
            font-size: 1.5rem;
            margin-bottom: 24px;
            background: linear-gradient(135deg,
                rgba(0, 234, 255, 1) 0%,
                rgba(100, 200, 255, 0.9) 50%,
                rgba(0, 102, 255, 1) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-shadow: 0 0 30px rgba(0, 234, 255, 0.5);
            letter-spacing: 2px;
            position: relative;
        }}

        .logo::after {{
            content: "";
            position: absolute;
            bottom: -8px;
            left: 50%;
            transform: translateX(-50%);
            width: 60px;
            height: 2px;
            background: linear-gradient(90deg,
                transparent 0%,
                rgba(0, 234, 255, 0.8) 50%,
                transparent 100%);
            border-radius: 1px;
        }}

        input {{
            width: 100%;
            padding: 18px 20px;
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            color: white;
            margin-bottom: 24px;
            text-align: center;
            font-size: 1.4rem;
            letter-spacing: 3px;
            outline: none;
            transition: all 0.4s ease;
            box-shadow:
                0 8px 20px rgba(0,0,0,0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
            position: relative;
        }}

        input::placeholder {{
            color: rgba(255, 255, 255, 0.6);
            font-weight: 300;
        }}

        input:focus {{
            border-color: rgba(0, 234, 255, 0.6);
            background: rgba(255, 255, 255, 0.12);
            box-shadow:
                0 0 30px rgba(0, 234, 255, 0.3),
                0 12px 30px rgba(0,0,0,0.4),
                inset 0 1px 0 rgba(255, 255, 255, 0.2);
            transform: translateY(-2px);
        }}

        .radio-group {{
            display: flex;
            gap: 16px;
            margin-bottom: 28px;
        }}

        .radio-card {{
            flex: 1;
            padding: 16px 20px;
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.15);
            cursor: pointer;
            transition: all 0.4s ease;
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(15px);
            -webkit-backdrop-filter: blur(15px);
            box-shadow:
                0 8px 20px rgba(0,0,0,0.25),
                inset 0 1px 0 rgba(255, 255, 255, 0.08);
            position: relative;
            overflow: hidden;
        }}

        .radio-card::before {{
            content: "";
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg,
                transparent,
                rgba(255, 255, 255, 0.1),
                transparent);
            transition: left 0.6s ease;
        }}

        .radio-card:hover {{
            border-color: rgba(0, 234, 255, 0.4);
            background: rgba(255, 255, 255, 0.08);
            box-shadow:
                0 12px 30px rgba(0,0,0,0.35),
                0 0 25px rgba(0, 234, 255, 0.15),
                inset 0 1px 0 rgba(255, 255, 255, 0.12);
            transform: translateY(-3px);
        }}

        .radio-card:hover::before {{
            left: 100%;
        }}

        .radio-card input {{
            display: none;
        }}

        .radio-card.active {{
            border-color: rgba(0, 234, 255, 0.8);
            background: rgba(0, 234, 255, 0.15);
            box-shadow:
                0 15px 35px rgba(0,0,0,0.4),
                0 0 40px rgba(0, 234, 255, 0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.2);
            transform: translateY(-2px);
        }}

        .btn {{
            background: linear-gradient(135deg,
                rgba(0, 102, 255, 0.9) 0%,
                rgba(0, 234, 255, 0.9) 100%);
            border: 1px solid rgba(255, 255, 255, 0.2);
            width: 100%;
            padding: 18px 24px;
            border-radius: 18px;
            font-weight: 700;
            cursor: pointer;
            color: white;
            transition: all 0.4s ease;
            box-shadow:
                0 10px 25px rgba(0,0,0,0.4),
                0 0 30px rgba(0, 102, 255, 0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.2);
            position: relative;
            overflow: hidden;
            font-size: 1.1rem;
            letter-spacing: 1px;
        }}

        .btn:hover {{
            background: linear-gradient(135deg,
                rgba(0, 234, 255, 1) 0%,
                rgba(0, 255, 170, 1) 100%);
            border-color: rgba(0, 255, 170, 0.8);
            box-shadow:
                0 12px 35px rgba(0,0,0,0.5),
                0 0 40px rgba(0, 255, 170, 0.6),
                0 0 20px rgba(0, 234, 255, 0.4),
                inset 0 1px 0 rgba(255, 255, 255, 0.4);
            transform: translateY(-3px) scale(1.02);
        }}

        .btn:active, .btn.clicked {{
            background: linear-gradient(135deg,
                rgba(0, 255, 170, 0.9) 0%,
                rgba(0, 234, 255, 0.9) 100%);
            border-color: rgba(0, 255, 170, 1);
            box-shadow:
                0 5px 15px rgba(0,0,0,0.4),
                0 0 30px rgba(0, 255, 170, 0.8),
                0 0 15px rgba(0, 234, 255, 0.6),
                inset 0 2px 5px rgba(0,0,0,0.2);
            transform: translateY(1px) scale(0.98);
        }}

        .success {{
            background: rgba(34, 197, 94, 0.15);
            border: 1px solid rgba(34, 197, 94, 0.3);
            color: #22c55e;
            padding: 16px 20px;
            border-radius: 14px;
            margin-bottom: 20px;
            font-weight: 600;
        }}

        .error {{
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: #ef4444;
            padding: 16px 20px;
            border-radius: 14px;
            margin-bottom: 20px;
            font-weight: 600;
        }}

        /* FUNDO */
        #bg-tech {{
            position: fixed;
            top: 0;
            left: 0;
            z-index: -1;
            opacity: 0.35;
            pointer-events: none;
        }}
        </style>

        <script>
        function enviarForm() {{
            const btn = document.querySelector('.btn');
            if(btn) {{
                btn.classList.add('clicked');
                btn.innerHTML = 'Enviando...';
            }}
            const loading = document.getElementById('loading');
            if(loading) {{
                loading.style.display = 'block';
            }}
        }}

        function atualizarRadar() {{
            const lista = document.getElementById('lista-radar');
            lista.innerHTML = '<p style="color:var(--primary); font-size:0.8rem; text-align:center;">Escaneando...</p>';
            // Aqui você chamaria sua rota de scan
        }}

        function limitarInput(el) {{
            el.value = el.value.replace(/\\D/g, '');
            if (el.value.length > 4) {{
                el.value = el.value.slice(0, 4);
            }}
        }}

        document.addEventListener("DOMContentLoaded", () => {{

            const cards = document.querySelectorAll('.radio-card');
            cards.forEach(card => {{
                card.addEventListener('click', () => {{
                    cards.forEach(c => c.classList.remove('active'));
                    card.classList.add('active');
                    card.querySelector('input').checked = true;
                }});
            }});

            const canvas = document.getElementById("bg-tech");
            if (!canvas) return;

            const ctx = canvas.getContext("2d");

            function resize() {{
                canvas.width = window.innerWidth;
                canvas.height = window.innerHeight;
            }}

            resize();
            window.addEventListener("resize", resize);

            let particles = [];
            let time = 0;

            class Particle {{
                constructor() {{
                    this.x = Math.random() * canvas.width;
                    this.y = Math.random() * canvas.height;
                    this.speedX = (Math.random() - 0.5) * 0.008;
                    this.speedY = (Math.random() - 0.5) * 0.008;
                    this.pulseOffset = Math.random() * Math.PI * 2;
                }}

                update() {{
                    this.x += this.speedX;
                    this.y += this.speedY;
                    if (this.x < 0 || this.x > canvas.width) this.speedX *= -1;
                    if (this.y < 0 || this.y > canvas.height) this.speedY *= -1;
                }}

                draw() {{
                    const pulse = Math.sin(time * 0.0008 + this.pulseOffset) * 0.4 + 0.8;
                    const radius = 2.5 * pulse;
                    ctx.fillStyle = 'rgba(100, 200, 255, 0.8)';
                    ctx.beginPath();
                    ctx.arc(this.x, this.y, radius, 0, Math.PI * 2);
                    ctx.fill();
                }}
            }}

            function init() {{
                for (let i = 0; i < 45; i++) {{
                    particles.push(new Particle());
                }}
            }}

            function connect() {{
                for (let a = 0; a < particles.length; a++) {{
                    for (let b = a; b < particles.length; b++) {{
                        let dx = particles[a].x - particles[b].x;
                        let dy = particles[a].y - particles[b].y;
                        let dist = dx * dx + dy * dy;
                        if (dist < 15000) {{
                            ctx.strokeStyle = `rgba(100, 200, 255, ${{0.2}})`;
                            ctx.lineWidth = 1;
                            ctx.beginPath();
                            ctx.moveTo(particles[a].x, particles[a].y);
                            ctx.lineTo(particles[b].x, particles[b].y);
                            ctx.stroke();
                        }}
                    }}
                }}
            }}

            function animate() {{
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                time++;
                particles.forEach(p => {{
                    p.update();
                    p.draw();
                }});
                connect();
                requestAnimationFrame(animate);
            }}

            init();
            animate();
        }});
        </script>

    </head>

    <body>

        <canvas id="bg-tech"></canvas>

        <div class="container">
            <div class="logo">ZERO48 TECH</div>

           
            <div class="radar-section">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="color: var(--primary); font-size: 0.9rem; margin: 0;">Pedidos</h3>
                    <button onclick="atualizarRadar()" class="btn-mini">SCANEAR</button>
                </div>
                <div id="lista-radar" class="radar-container">
                    <p style="color: #64748b; font-size: 0.7rem; text-align: center;">Aguardando scan...</p>
                </div>
            </div>

            {conteudo}
        </div>

    </body>
    </html>
    """


# =============================================================================
# 🌐 ROTA GET "/" (O que o usuário vê ao abrir o site)
# =============================================================================
@app.get("/", response_class=HTMLResponse)
def pagina():
    """
    Esta função cria a página principal.
    Ela desenha o campo de entrada e o botão 'Enviar'.
    """
    conteudo = """
    <h3>Digite o número do seu pedido aqui</h3><br><br>

<form action="/enviar" method="post" onsubmit="enviarForm()">

    <input 
        name="numero"
        placeholder="EX:5059"
        maxlength="4"   
        inputmode="numeric"
        oninput="limitarInput(this)"
        required
    >

    <div class="radio-group">
        <label class="radio-card">
            <input type="radio" name="bot" value="Nipô" required>
            Nipô
        </label>

        <label class="radio-card">
            <input type="radio" name="bot" value="Ene">
            Ene
        </label>
    </div>

    <button class="btn" type="submit">Enviar</button>

    <div id="loading" class="loading">
        
    </div>

</form>
"""
    return layout(conteudo)


# =============================================================================
# 📩 ROTA POST "/enviar" (O Servidor recebendo o formulário)
# =============================================================================
@app.post("/enviar", response_class=HTMLResponse)
def receber_form(numero: str = Form(...), bot: str = Form(...)):
    """
    Esta função processa o que o usuário enviou.
    Ela valida o dado e o guarda na 'memória global' do servidor.
    """
    global numero_form, bot_selecionado

    # Verifica se são 4 números. Se não for, mostra erro.
    if not numero.isdigit() or len(numero) != 4:
        conteudo = """
        <div class="error">❌ Digite exatamente 4 números</div>
        <a href="/">Voltar</a>
        """
        return layout(conteudo)

    if bot not in BOT_CONFIGS:
        conteudo = """
        <div class="error">❌ Bot inválido. Escolha Nipô ou Ene.</div>
        <a href="/">Voltar</a>
        """
        return layout(conteudo)

    # Guarda o número e o bot selecionado
    numero_form = numero
    bot_selecionado = bot

    fila = BOT_CONFIGS[bot]["fila"]
    fila.add(numero_form)

    print("📥 Número do pedido RECEBIDO manualmente pelo seu Formulário:", numero_form)
    print(f"📝 Pedido enviado para o bot {bot}.")

    conteudo = f"""
    <style>
        .botao-despacho {{
            background: linear-gradient(135deg, #FFE66D 0%, #FFEB99 100%);
            color: #333;
            padding: 12px 24px;
            text-decoration: none;
            font-weight: 600;
            border: 2px solid #FF6B6B;
            border-radius: 8px;
            display: inline-block;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(255, 107, 107, 0.3);
            font-size: 16px;
        }}
        .botao-despacho:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(255, 107, 107, 0.4);
            background: linear-gradient(135deg, #FFEB99 0%, #FFF0B3 100%);
        }}
        .botao-despacho:active {{
            transform: translateY(0);
            box-shadow: 0 2px 8px rgba(255, 107, 107, 0.3);
        }}
    </style>
    <div class="success">✅ Pedido Enviado!</div>
    <p> Loja selecionada: {bot}</p>
    <p> Aguarde o pedido chegar: {numero_form}</p>
    <a href="/" class="botao-despacho">Despachar Outro</a>
    """
    return layout(conteudo)


# =============================================================================
# 📡 BOT 3 - RADAR DE CAPTURA (APENAS LEITURA)
# =============================================================================


@app.get("/radar-pedidos")
async def radar_pedidos():
    # Usamos a conta da Nipô como base para o scraping
    config = BOT_CONFIGS["Nipô"]
    pedidos_capturados = []

    try:
        async with async_playwright() as p:
            # Launch rápido em modo headless para não pesar
            browser = await p.chromium.launch(headless=True)
            context = await p.chromium.launch_persistent_context(
                user_data_dir=config["user_data_dir"], headless=True
            )
            page = context.pages[0]

            await page.goto(URL_PEDIDOS, timeout=30000)

            if "login" in page.url:
                await fazer_login(page, config["email"], config["senha"])
                await page.goto(URL_PEDIDOS)

            # Aguarda a lista de pedidos carregar
            await page.wait_for_selector("#lista-pedidos_esperando", timeout=15000)

            # Localiza todos os blocos de pedidos na tela
            elementos = page.locator("#lista-pedidos_esperando > div")
            total = await elementos.count()

            for i in range(total):
                pedido_el = elementos.nth(i)

                # Extração do Número
                num_bruto = await pedido_el.locator(
                    "span.request-number"
                ).text_content()
                numero = num_bruto.replace("#", "").strip()

                # Extração do Endereço
                # (Ajuste o seletor conforme o HTML real: .address-text ou similar)
                try:
                    endereco = await pedido_el.locator(
                        ".address-info, .address-detail"
                    ).first.text_content()
                except:
                    endereco = "Endereço não disponível na prévia"

                pedidos_capturados.append(
                    {"numero": numero, "endereco": endereco.strip()}
                )

            await context.close()
            return {"status": "sucesso", "dados": pedidos_capturados}

    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}


# =============================================================================
# 🔔 ROTA POST "/webhook" (O Robô que recebe avisos externos)
# =============================================================================
@app.post("/webhook")
async def receber_webhook(request: Request, dados: dict = Body(...)):
    """
    Recebe webhook, valida segurança e dispara o bot automaticamente
    """
    global numero_form

    # ==============================
    # 🛡️ VALIDAÇÃO DE ASSINATURA
    # ==============================
    assinatura_recebida = request.headers.get("Signature-V2")
    corpo_bruto = await request.body()

    # NOTA: Certifique-se de que a variável API_KEY está definida de forma segura!
    # API_KEY = "sua_chave_secreta_aqui"
    try:
        chave_secreta = API_KEY.encode("utf-8")
        assinatura_calculada = hmac.new(
            chave_secreta, corpo_bruto, hashlib.sha512
        ).hexdigest()

        if assinatura_recebida != assinatura_calculada:
            print("🚨 Assinatura inválida!")
            return {"status": "erro_autenticacao"}
    except NameError:
        print(
            "⚠️ AVISO: API_KEY não definida! Pulando verificação de segurança temporariamente. Defina sua API_KEY no código!"
        )

    print("✅ Webhook válido (ou proteção pulada)!")

    # ==============================
    # 🔎 EXTRAÇÃO DOS DADOS
    # ==============================
    evento = dados.get("event")
    pagamento = dados.get("payment", {})
    status = pagamento.get("status")

    numero_webhook = dados.get("numero") or pagamento.get("externalReference")

    print(f"📦 Número vindo do webhook: {numero_webhook}")
    print(f"📦 Número guardado no formulário atual: {numero_form}")

    # ==============================
    # 🎯 FILTROS
    # ==============================
    if evento and evento != "PAYMENT_RECEIVED":
        print("⛔ Evento ignorado (não é pagamento):", evento)
        return {"status": "ignorado"}

    if status and status != "CONFIRMED":
        print("⏳ Pagamento detectado, mas ainda está pendente:", status)
        return {"status": "aguardando"}

    # ==============================
    # 🔥 MATCH + DISPARO DO BOT
    # ==============================
    if numero_webhook and numero_form and bot_selecionado:
        if str(numero_webhook) == str(numero_form):
            print(
                f"🔥 MATCH CONFIRMADO! O pedido {numero_webhook} foi pago com sucesso!"
            )

            bot_queue = BOT_CONFIGS.get(bot_selecionado, {}).get("fila")
            if bot_queue is not None:
                bot_queue.add(str(numero_webhook))
                print(
                    f"📝 Anotado! Pedido {numero_webhook} jogado na fila do bot {bot_selecionado}."
                )
            else:
                print(f"⚠️ Bot selecionado inválido no webhook: {bot_selecionado}")
        else:
            print(
                f"❌ NÃO BATEU: Webhook enviou {numero_webhook}, mas no formulário era {numero_form}"
            )
    else:
        print(
            "⚠️ Dados incompletos: Faltou número na API, no formulário ou escolha de bot."
        )

    return {"status": "ok"}


# =============================================================================
# 🚀 START PARA EXECUÇÃO (Dando a partida no servidor)
# =============================================================================

if __name__ == "__main__":
    # O bot não sobe mais por aqui, ele sobe no evento "startup" do FastAPI lá em cima!

    import uvicorn

    port = int(os.environ.get("PORT", 8000))

    uvicorn.run("main:app", host="0.0.0.0", port=port) #reload=True)
