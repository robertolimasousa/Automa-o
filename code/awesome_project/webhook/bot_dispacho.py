import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# ==============================================================================
# 🔗 CONFIGURAÇÃO DE URLs DO SISTEMA
# ==============================================================================
URL_LOGIN = "https://cloud.machine.global/site/login"
URL_PEDIDOS = "https://cloud.machine.global/solicitacao/gestaoPedido"


async def goto_com_retry(page, url, max_retries=3, timeout=60000, wait_until="domcontentloaded"):
    """Navega para a URL com retries em caso de Timeout ou falha temporária."""
    for tentativa in range(1, max_retries + 1):
        try:
            print(f"🌐 Navegando para {url} (tentativa {tentativa}/{max_retries})")
            return await page.goto(url, timeout=timeout, wait_until=wait_until)
        except PlaywrightTimeoutError as e:
            print(f"⚠️ Timeout ao carregar {url} ({e}). Tentativa {tentativa}/{max_retries}")
            if tentativa == max_retries:
                raise
            await page.wait_for_timeout(2000)
            try:
                await page.reload(timeout=timeout, wait_until=wait_until)
            except Exception:
                pass
        except Exception as e:
            print(f"⚠️ Erro ao navegar para {url}: {e}")
            if tentativa == max_retries:
                raise
            await page.wait_for_timeout(2000)
    raise Exception(f"❌ Impossível navegar para {url} após {max_retries} tentativas")


# ==============================================================================
# 🔐 FUNÇÃO DE LOGIN
# ==============================================================================
async def fazer_login(page, email, senha):
    """Preenche os dados de usuário e senha na página de login e entra no sistema."""
    print("🔐 Fazendo login...")
    await goto_com_retry(page, URL_LOGIN)

    for tentativa in range(5):
        try:
            print(f"🔄 Tentativa login {tentativa + 1}")

            username = page.locator("#LoginForm_username")
            password = page.locator("#LoginForm_password")
            entrar_botao = page.locator("#entrar")

            await username.wait_for(state="visible", timeout=15000)
            await password.wait_for(state="visible", timeout=15000)
            await entrar_botao.wait_for(state="visible", timeout=15000)

            await username.fill(email)
            await password.fill(senha)
            await page.wait_for_timeout(500)
            await entrar_botao.click()

            try:
                await page.wait_for_selector("#menu-lateral", timeout=20000)
            except Exception:
                if "login" not in page.url:
                    print("⚠️ Login parece ter ocorrido, mas '#menu-lateral' não apareceu. Verificando URL e continuando.")
                    return
                raise

            print("✅ Login realizado com sucesso!")
            return

        except Exception as e:
            print(f"⚠️ Erro login: {e}")
            if page.is_closed():
                raise Exception("❌ Página fechada durante o processo de login") from e
            await page.wait_for_timeout(2000)
            await page.reload()
            await page.wait_for_load_state("domcontentloaded")

    raise Exception("❌ Falha no login")


# ==============================================================================
# 📦 FUNÇÃO DE ESPERA DA LISTA DE PEDIDOS
# ==============================================================================
async def esperar_lista_carregar(page):
    """Garante que a lista onde os pedidos chegam carregou, usando seletores mais robustos."""
    # Seletores potenciais para a lista de pedidos
    potential_selectors = [
        "#link-pedidos_esperando",   # Seletor correto identificado
        "#lista-pedidos_esperando",  # Seletor antigo (fallback)
        "div.dataTables_wrapper",    # Um seletor comum para tabelas de dados
        "#gestaoPedido-grid",        # Outro ID potencial baseado na URL
        "div.grid-view",             # Classe genérica para visualização em grade
        "table.items",               # Tabela comum para listagens
        "div[role=\"main\"]",        # Área principal de conteúdo
    ]

    for tentativa in range(1, 3): # Tentar algumas vezes com diferentes seletores
        print(f"📡 Aguardando lista de pedidos carregar (tentativa {tentativa})...")
        await page.wait_for_load_state("domcontentloaded")

        for selector in potential_selectors:
            try:
                print(f"  Tentando seletor: {selector}")
                await page.wait_for_selector(selector, state="attached", timeout=15000) # Reduzir timeout para testar mais rápido
                print(f"✅ Lista de pedidos carregada com seletor: {selector}!")
                return page.locator(selector)
            except PlaywrightTimeoutError:
                print(f"  Seletor {selector} não encontrado em 15s.")
            except Exception as e:
                print(f"  Erro ao tentar seletor {selector}: {e}")

        # Se nenhum seletor funcionou na primeira tentativa, tentar recarregar a página
        if tentativa == 1:
            print("⚠️ Nenhum seletor encontrado. Tentando atualização leve da página...")
            try:
                await page.reload(wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(5000) # Dar um tempo para a página renderizar
            except Exception as reload_error:
                print(f"⚠️ Erro no reload: {reload_error}")

    # Se todas as tentativas falharem, logar o HTML para diagnóstico
    print("❌ Falha ao carregar a lista de pedidos após múltiplas tentativas e seletores.")
    print("Capturando HTML da página para diagnóstico...")
    page_content = await page.content()
    with open(f"page_content_error_{time.time()}.html", "w", encoding="utf-8") as f:
        f.write(page_content)
    print(f"HTML da página salvo em page_content_error_{time.time()}.html")
    raise Exception("❌ Impossível carregar a lista de pedidos. Verifique o HTML salvo para diagnóstico.")

    # Retornar um locator vazio ou levantar exceção se a lista não for encontrada
    # return page.locator("#lista-pedidos_esperando") # Manter o original como fallback se necessário, mas a exceção é mais clara


# ==============================================================================
# 🤖 BOT PRINCIPAL - MONITORAMENTO DE PEDIDOS
# ==============================================================================
def limpar_numero(texto):
    """Função auxiliar modificada: Remove espaços e símbolos, mantendo zeros à esquerda."""
    if not texto:
        return ""
    # Corrigido: Não remove mais os zeros usando lstrip para preservar formatos como '0188'
    return str(texto).replace("#", "").replace("\n", "").replace("\t", "").strip()


async def executar_automacao(
    user_data_dir="user_data",
    email="niposushidelivery@outlook.com",
    senha="Nipo4145!",
    fila_pedidos_param=None,
    fila_lock=None,
    bot_name="Default",
):
    # Passa a usar diretamente a referência da fila criada no main.py
    if fila_pedidos_param is not None:
        fila_local_referencia = fila_pedidos_param
    else:
        fila_local_referencia = set()

    print(f"🤖 Bot {bot_name} ativado (Modo 24/7): Aguardando comandos na fila!")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=True,
            slow_mo=100,
            args=["--no-sandbox"]
        )

        page = context.pages[0] if context.pages else await context.new_page()
        await goto_com_retry(page, URL_PEDIDOS)

        if "login" in page.url:
            await fazer_login(page, email, senha)
            await goto_com_retry(page, URL_PEDIDOS)

        lista = await esperar_lista_carregar(page)
        print(f"📦 Sistema {bot_name} pronto - loop de monitoramento iniciado...")

        pedidos_processados = set()
        pedidos_logados = set()
        ultimo_status_vazio = False

        while True:
            try:
                if "login" in page.url:
                    print("⚠️ Sessão expirada, relogando...")
                    await fazer_login(page, email, senha)
                    await page.goto(URL_PEDIDOS)
                    lista = await esperar_lista_carregar(page)

                elementos = lista.locator("xpath=./div")
                total = await elementos.count()

                if total == 0:
                    if not ultimo_status_vazio:
                        print(f"📭 [{bot_name}] Nenhum pedido pendente na plataforma. Aguardando...")
                        ultimo_status_vazio = True
                else:
                    ultimo_status_vazio = False

                # Coleta e limpa os itens direto da fila compartilhada viva com segurança de thread
                if fila_lock:
                    with fila_lock:
                        fila_normalizada = {limpar_numero(x) for x in fila_local_referencia if x}
                else:
                    fila_normalizada = {limpar_numero(x) for x in fila_local_referencia if x}

                for i in range(total):
                    pedido = elementos.nth(i)

                    try:
                        numero_alvo = pedido.locator("span.request-number").first
                        if await numero_alvo.count() == 0:
                            continue

                        numero_bruto = await numero_alvo.evaluate("(el) => el.textContent")
                        numero = limpar_numero(numero_bruto)

                        if not numero or numero in pedidos_processados:
                            continue

                        if numero not in pedidos_logados:
                            print(f"🔎 Pedido encontrado na tela [{bot_name}]: {numero}")
                            pedidos_logados.add(numero)
                            print(f"📥 FILA ATIVA [{bot_name}]: {fila_normalizada}")

                        # 🎯 MATCH (Garante tratamento exato das strings lidas)
                        if numero in fila_normalizada:
                            print(f"🔥 MATCH ENCONTRADO: {numero} consta na fila do bot {bot_name}!")

                            # Localiza o ícone/botão de despacho
                            botao_icone = pedido.locator("div.set.row-status > button > i.material-icons.notranslate.despacho").first
                            
                            # Clique via injeção JavaScript (Evita erros por bloqueio de tela)
                            await botao_icone.evaluate("el => el.click()")

                            # Aguarda resposta visual da plataforma
                            await page.wait_for_timeout(3000)
                            print(f"🚀 Pedido {numero} despachado com sucesso!")

                            # Atualiza controle local
                            pedidos_processados.add(numero)

                            # Remove o item limpo correspondente de dentro do set original do main.py com segurança de thread
                            if fila_lock:
                                with fila_lock:
                                    for item in list(fila_local_referencia):
                                        if limpar_numero(item) == numero:
                                            fila_local_referencia.remove(item)
                                            print(f"🗑️ Pedido {numero} removido da fila operacional.")
                                            break
                            else:
                                for item in list(fila_local_referencia):
                                    if limpar_numero(item) == numero:
                                        fila_local_referencia.remove(item)
                                        print(f"🗑️ Pedido {numero} removido da fila operacional.")
                                        break

                    except Exception as e:
                        print(f"⚠️ Erro ao interagir com o pedido específico do índice {i}: {e}")

                # Janela de verificação a cada 5 segundos
                await page.wait_for_timeout(5000)

            except Exception as e:
                print(f"⚠️ Erro geral no loop principal do {bot_name}: {e}")
                await page.wait_for_timeout(2000)


# ==============================================================================
# ▶️ PONTO DE PARTIDA LOCAL (TESTES ISOLADOS)
# ==============================================================================
if __name__ == "__main__":
    teste_fila = set()
    teste_fila.add("0188")
    asyncio.run(executar_automacao(fila_pedidos_param=teste_fila, bot_name="Teste Local"))