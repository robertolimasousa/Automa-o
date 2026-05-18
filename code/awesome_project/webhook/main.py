# =============================================================================
# 📦 IMPORTAÇÕES (As Ferramentas que o Python vai usar)
# =============================================================================
from fastapi import FastAPI, Form, Request, Body
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Optional
from contextlib import asynccontextmanager
import os
import hmac
import hashlib
from threading import Thread
import asyncio
import time

# Importações internas do seu projeto
from .bot_dispacho import executar_automacao, fazer_login, URL_PEDIDOS

# =============================================================================
# 🔑 CONFIGURAÇÕES DE SEGURANÇA (Evita o bug de NameError no Webhook)
# =============================================================================
# Defina aqui a mesma chave configurada no seu gateway de pagamento/webhook
API_KEY = os.environ.get("API_KEY", "SUA_CHAVE_SECRETA_PADRAO_AQUI")

# =============================================================================
# 🚀 INICIALIZAÇÃO (Ligando os motores)
# =============================================================================
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

# =============================================================================
# 🔥 WORKER DOS BOTS (Trabalhador em Segundo Plano)
# =============================================================================
def start_worker(user_data_dir, email, senha, fila_pedidos, bot_name):
    while True:
        try:
            print(f"🚀 Iniciando o Trabalhador background do bot {bot_name}...")

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Executa a automação passando a fila correta de cada bot
            loop.run_until_complete(
                executar_automacao(
                    user_data_dir=user_data_dir,
                    email=email,
                    senha=senha,
                    fila_pedidos=fila_pedidos,
                    bot_name=bot_name,
                )
            )

        except Exception as e:
            print(f"❌ Erro crítico no bot {bot_name}: {e}")

        print(f"🔄 Reiniciando bot {bot_name} em 10 segundos...")
        time.sleep(10)

# =============================================================================
# 🚀 LIFESPAN FASTAPI
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # BOT NIPÔ
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

    # BOT ENE
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

# =============================================================================
# 🚀 APP FASTAPI
# =============================================================================
app = FastAPI(lifespan=lifespan)

# 🧠 VARIÁVEIS GLOBAIS
numero_form: Optional[str] = None
bot_selecionado: Optional[str] = None

# =============================================================================
# 🎨 FUNÇÃO DE LAYOUT (Interface Visual)
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
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Outfit', sans-serif;
            background: linear-gradient(135deg, #1a3a52 0%, #0a1929 100%);
            display: flex; justify-content: center; align-items: center;
            min-height: 100vh; color: var(--text); padding: 20px;
        }}
        .container {{
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(40px) saturate(180%);
            -webkit-backdrop-filter: blur(40px) saturate(180%);
            width: 100%; max-width: 420px; padding: 40px; border-radius: 32px;
            border: 1px solid rgba(255, 255, 255, 0.18);
            box-shadow: 0 25px 50px rgba(0,0,0,0.5), 0 0 60px rgba(0, 234, 255, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.2);
            text-align: center; position: relative; overflow: hidden;
            animation: float 6s ease-in-out infinite;
        }}
        .radar-section {{ margin-bottom: 25px; border-bottom: 1px solid rgba(0,234,255,0.2); padding-bottom: 20px; text-align: left; }}
        .btn-mini {{ background: rgba(0, 234, 255, 0.1); border: 1px solid var(--primary); color: var(--primary); padding: 5px 10px; border-radius: 8px; font-size: 0.7rem; font-weight: 700; cursor: pointer; transition: all 0.3s ease; }}
        .btn-mini:hover {{ background: var(--primary); color: #000; }}
        .radar-container {{ max-height: 220px; overflow-y: auto; margin-top: 10px; background: rgba(0,0,0,0.2); border-radius: 12px; padding: 8px; }}
        .pedido-card {{ background: rgba(255,255,255,0.06); border: 1px solid rgba(0,234,255,0.15); border-radius: 12px; padding: 10px; margin-bottom: 10px; }}
        .pedido-numero {{ color: var(--primary); font-weight: 700; font-size: 0.9rem; margin-bottom: 5px; }}
        .pedido-endereco {{ color: #cbd5e1; font-size: 0.75rem; line-height: 1.4; }}
        @keyframes float {{ 0%, 100% {{ transform: translateY(0px); }} 50% {{ transform: translateY(-5px); }} }}
        .logo {{ font-weight: 800; font-size: 1.5rem; margin-bottom: 24px; background: linear-gradient(135deg, rgba(0, 234, 255, 1) 0%, rgba(100, 200, 255, 0.9) 50%, rgba(0, 102, 255, 1) 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; text-shadow: 0 0 30px rgba(0, 234, 255, 0.5); letter-spacing: 2px; }}
        input {{ width: 100%; padding: 18px 20px; border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.2); background: rgba(255, 255, 255, 0.08); color: white; margin-bottom: 24px; text-align: center; font-size: 1.4rem; letter-spacing: 3px; outline: none; }}
        .radio-group {{ display: flex; gap: 16px; margin-bottom: 28px; }}
        .radio-card {{ flex: 1; padding: 16px 20px; border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.15); cursor: pointer; transition: all 0.4s ease; background: rgba(255, 255, 255, 0.05); }}
        .radio-card input {{ display: none; }}
        .radio-card.active {{ border-color: rgba(0, 234, 255, 0.8); background: rgba(0, 234, 255, 0.15); }}
        .btn {{ background: linear-gradient(135deg, rgba(0, 102, 255, 0.9) 0%, rgba(0, 234, 255, 0.9) 100%); width: 100%; padding: 18px 24px; border-radius: 18px; font-weight: 700; cursor: pointer; color: white; border: none; font-size: 1.1rem; }}
        .success {{ background: rgba(34, 197, 94, 0.15); border: 1px solid rgba(34, 197, 94, 0.3); color: #22c55e; padding: 16px 20px; border-radius: 14px; margin-bottom: 20px; font-weight: 600; }}
        .error {{ background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); color: #ef4444; padding: 16px 20px; border-radius: 14px; margin-bottom: 20px; font-weight: 600; }}
        #bg-tech {{ position: fixed; top: 0; left: 0; z-index: -1; opacity: 0.35; pointer-events: none; }}
        </style>
        <script>
        async function atualizarRadar() {{
            const lista = document.getElementById('lista-radar');
            try {{
                const response = await fetch('/radar-pedidos');
                const data = await response.json();
                if (data.status !== 'sucesso') {{
                    lista.innerHTML = `<p style="color:red; font-size:0.8rem;">Erro ao buscar pedidos</p>`;
                    return;
                }}
                if (data.dados.length === 0) {{
                    lista.innerHTML = `<p style="color:#94a3b8; font-size:0.8rem; text-align:center;">Nenhum pedido na fila</p>`;
                    return;
                }}
                let html = '';
                data.dados.forEach(pedido => {{
                    html += `
                        <div class="pedido-card">
                            <div class="pedido-numero">Pedido #${{pedido.numero}}</div>
                            <div class="pedido-endereco">${{pedido.endereco}}</div>
                        </div>
                    `;
                }});
                lista.innerHTML = html;
            }} catch (erro) {{
                lista.innerHTML = `<p style="color:red; font-size:0.8rem;">Erro interno ao carregar radar</p>`;
            }}
        }}
        function enviarForm() {{
            const btn = document.querySelector('.btn');
            if(btn) {{ btn.innerHTML = 'Enviando...'; }}
        }}
        function limitarInput(el) {{
            el.value = el.value.replace(/\\D/g, '');
            if (el.value.length > 4) {{ el.value = el.value.slice(0, 4); }}
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
            atualizarRadar();
            setInterval(atualizarRadar, 30000);
        }});
        </script>
    </head>
    <body>
        <canvas id="bg-tech"></canvas>
        <div class="container">
            <div class="logo">ZERO48 TECH</div>
            <div class="radar-section">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <h3 style="color: var(--primary); font-size: 0.9rem;">Fila de Despacho</h3>
                    <button onclick="atualizarRadar()" class="btn-mini">SCANEAR</button>
                </div>
                <div id="lista-radar" class="radar-container">
                    <p style="color:#64748b;font-size:0.7rem;text-align:center;">Carregando...</p>
                </div>
            </div>
            {conteudo}
        </div>
    </body>
    </html>
    """

# =============================================================================
# 🌐 ROTA GET "/"
# =============================================================================
@app.get("/", response_class=HTMLResponse)
def pagina():
    conteudo = """
    <h3>Digite o número do seu pedido aqui</h3>
    <br><br>
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
                <input type="radio" name="bot" value="Nipô" required> Nipô
            </label>
            <label class="radio-card">
                <input type="radio" name="bot" value="Ene"> Ene
            </label>
        </div>
        <button class="btn" type="submit">Enviar</button>
    </form>
    """
    return layout(conteudo)

# =============================================================================
# 📩 ROTA POST "/enviar"
# =============================================================================
@app.post("/enviar", response_class=HTMLResponse)
def receber_form(numero: str = Form(...), bot: str = Form(...)):
    global numero_form
    global bot_selecionado

    if not numero.isdigit() or len(numero) != 4:
        conteudo = """
        <div class="error">❌ Digite exatamente 4 números</div>
        <a href="/">Voltar</a>
        """
        return layout(conteudo)

    if bot not in BOT_CONFIGS:
        conteudo = """
        <div class="error">❌ Bot inválido</div>
        <a href="/">Voltar</a>
        """
        return layout(conteudo)

    numero_form = numero
    bot_selecionado = bot

    fila = BOT_CONFIGS[bot]["fila"]
    fila.add(numero_form)

    print("📥 Número recebido via formulário:", numero_form)
    print(f"🤖 Bot escolhido: {bot}")

    conteudo = f"""
    <div class="success">✅ Pedido enviado com sucesso!</div>
    <p>Loja selecionada: {bot}</p>
    <br>
    <p>Pedido: {numero_form}</p>
    <br><br>
    <a href="/" style="color:white; text-decoration:none; background:#0066ff; padding:12px 20px; border-radius:10px; display:inline-block;">
        Despachar Outro
    </a>
    """
    return layout(conteudo)

# =============================================================================
# 🎯 NOVA ROTA: GET "/radar-pedidos" (Corrige o erro 404 do front-end)
# =============================================================================
@app.get("/radar-pedidos")
def obter_radar_pedidos():
    """Retorna os números de pedidos ativos armazenados nas filas de cada robô."""
    dados_fila = []
    for nome_bot, config in BOT_CONFIGS.items():
        for pedido in config["fila"]:
            dados_fila.append({
                "numero": pedido,
                "endereco": f"Aguardando processamento automático ({nome_bot})."
            })
    return {"status": "sucesso", "dados": dados_fila}

# =============================================================================
# 🔔 ROTA POST "/webhook"
# =============================================================================
@app.post("/webhook")
async def receber_webhook(request: Request, dados: dict = Body(...)):
    global numero_form
    global bot_selecionado

    # 🛡️ VALIDAÇÃO DE ASSINATURA
    assinatura_recebida = request.headers.get("Signature-V2")
    corpo_bruto = await request.body()

    # Cálculo seguro do HMAC SHA512 usando a API_KEY global definida no topo
    chave_secreta = API_KEY.encode("utf-8")
    assinatura_calculada = hmac.new(
        chave_secreta,
        corpo_bruto,
        hashlib.sha512
    ).hexdigest()

    if signature_v2 := assinatura_recebida:
        if signature_v2 != signature_v2: # Verificação simples se o header foi enviado
            pass

    if assinatura_recebida != assinatura_calculada:
        print("🚨 Assinatura inválida!")
        return {"status": "erro_autenticacao"}

    print("✅ Webhook válido!")

    # 🔎 EXTRAÇÃO DOS DADOS
    evento = dados.get("event")
    pagamento = dados.get("payment", {})
    status = pagamento.get("status")
    numero_webhook = dados.get("numero") or pagamento.get("externalReference")

    print(f"📦 Número recebido no webhook: {numero_webhook}")

    # 🎯 FILTROS DO GATEWAY
    if evento and evento != "PAYMENT_RECEIVED":
        print("⛔ Evento ignorado")
        return {"status": "ignorado"}

    if status and status != "CONFIRMED":
        print("⏳ Pagamento pendente")
        return {"status": "aguardando"}

    # 🔥 AUTOMAÇÃO DO MATCH VIA WEBHOOK
    if numero_webhook and numero_form and bot_selecionado:
        if str(numero_webhook) == str(numero_form):
            print(f"🔥 MATCH CONFIRMADO: {numero_webhook}")
            
            bot_queue = BOT_CONFIGS.get(bot_selecionado, {}).get("fila")
            if bot_queue is not None:
                bot_queue.add(str(numero_webhook))
                print(f"📝 Pedido injetado com sucesso no bot {bot_selecionado}")
        else:
            print(f"❌ NÃO BATEU: Webhook ({numero_webhook}) diferente do Form ({numero_form})")
    else:
        print("⚠️ Dados globais ausentes para cruzamento de informações neste momento.")

    return {"status": "ok"}

# =============================================================================
# 🚀 START
# =============================================================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)