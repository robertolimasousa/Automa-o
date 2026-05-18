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
    """
    Objetivo: Preencher os dados de usuário e senha na página de login e entrar no sistema.
    """
    print("🔐 Fazendo login...")

    # Força a ida para a tela de login
    await goto_com_retry(page, URL_LOGIN)

    # Tentamos fazer o login até 5 vezes em caso de lentidão ou falhas temporárias
    for tentativa in range(5):
        try:
            print(f"🔄 Tentativa login {tentativa + 1}")

            # Localiza os campos de e-mail e senha pelo "ID" HTML na página web
            username = page.locator("#LoginForm_username")
            password = page.locator("#LoginForm_password")
            entrar_botao = page.locator("#entrar")

            # Aguarda garantindo que os campos carregaram e estão visíveis
            await username.wait_for(state="visible", timeout=15000)
            await password.wait_for(state="visible", timeout=15000)
            await entrar_botao.wait_for(state="visible", timeout=15000)

            # Preenche as credenciais
            await username.fill(email)
            await password.fill(senha)

            # Uma pequena pausa para evitar que a plataforma bloqueie preenchimentos muito rápidos (comportamento de robô)
            await page.wait_for_timeout(500)

            # Clica no botão "entrar" (localizado pelo id #entrar)
            await entrar_botao.click()

            # Após clicar em entrar, esperamos até que o menu lateral do painel apareça.
            # Essa é a confirmação visual de que o login deu certo!
            try:
                await page.wait_for_selector("#menu-lateral", timeout=20000)
            except Exception:
                if "login" not in page.url:
                    print("⚠️ Login parece ter ocorrido, mas '#menu-lateral' não apareceu. Verificando URL e continuando.")
                    return
                raise

            print("✅ Login realizado sucesso!")
            return

        except Exception as e:
            print(f"⚠️ Erro login: {e}")

            if page.is_closed():
                raise Exception("❌ Página fechada durante o processo de login") from e

            await page.wait_for_timeout(2000)
            await page.reload()
            await page.wait_for_load_state("domcontentloaded")

    # Se falhar nas 5 vezes, aborta o script.
    raise Exception("❌ Falha no login")


# ==============================================================================
# 📦 FUNÇÃO DE ESPERA DA LISTA DE PEDIDOS
# ==============================================================================
async def esperar_lista_carregar(page):
    """
    Garante que a lista onde os pedidos chegam carregou.
    Versão otimizada para Render.
    """

    try:
        print("📡 Aguardando lista de pedidos carregar...")

        # Espera apenas o HTML inicial carregar
        await page.wait_for_load_state("domcontentloaded")

        # Aguarda o container principal aparecer no DOM
        await page.wait_for_selector(
            "#lista-pedidos_esperando",
            state="attached",
            timeout=30000
        )

        # Pequena pausa para AJAX/renderização interna
        await page.wait_for_timeout(3000)

        print("✅ Lista de pedidos carregada!")

    except Exception as e:

        print(f"⚠️ Lista não apareceu inicialmente: {e}")

        print("🔄 Tentando atualização leve da página...")

        try:
            # Reload mais leve para Render
            await page.reload(
                wait_until="domcontentloaded",
                timeout=30000
            )

        except Exception as reload_error:
            print(f"⚠️ Erro no reload: {reload_error}")

        # Espera renderizar novamente
        await page.wait_for_timeout(5000)

        # Segunda tentativa
        await page.wait_for_selector(
            "#lista-pedidos_esperando",
            state="attached",
            timeout=30000
        )

        print("✅ Lista carregada após reload!")

    # Retorna a lista localizada
    lista = page.locator("#lista-pedidos_esperando")

    return lista
# ==============================================================================
# 🤖 BOT PRINCIPAL - MONITORAMENTO DE PEDIDOS
# ==============================================================================

# 📝 FILA GLOBAL DE PEDIDOS
# Nossa variável unificada. O main.py vai injetar os números novos aqui dentro!
fila_pedidos = set()

async def executar_automacao(
    user_data_dir="user_data",
    email="niposushidelivery@outlook.com",
    senha="Nipo4145!",
    fila_pedidos=None,
    bot_name="Default",
):
    if fila_pedidos is None:
        fila_pedidos = globals().get("fila_pedidos", set())

    print(f"🤖 Bot {bot_name} ativado (Modo 24/7): Olhando fixamente para a tela aguardando comandos caírem na fila!")

    # Inicia o motor do Playwright (Navegador)
    async with async_playwright() as p:

        # Cria/Conecta a uma pasta "persistente" no seu computador.
        # Isso significa que todos os cookies, sessões e logins vão ficar salvos na pasta '{user_data_dir}'.
        # slow_mo=100 atrasa cada ação do robô em 100 milissegundos para parecer mais humano aos olhos do sistema.
        context = await p.chromium.launch_persistent_context(
    user_data_dir=user_data_dir,
    headless=True,
    slow_mo=100,
    args=["--no-sandbox"]
)

        # Abre a primeira guia em branco do navegador
        page = context.pages[0] if context.pages else await context.new_page()

        # O robô vai direto para a página listagem de pedidos
        await goto_com_retry(page, URL_PEDIDOS)

        # Se a sessão expirou e o sistema da machine bloqueou o acesso exigindo login,
        # a URL vai mudar e a palavra "login" vai aparecer. Nesse caso, ele chama a função do login para se autenticar.
        if "login" in page.url:
            await fazer_login(page, email, senha)
            # Retorna para a página de pedidos após autenticar
            await goto_com_retry(page, URL_PEDIDOS)

        # Chamamos nossa função para segurar a execução até os primeiros pedidos aparecerem
        lista = await esperar_lista_carregar(page)

        print("📦 Sistema pronto - loop de monitoramento de pedidos iniciado...")

        # Bancos de dados na RAM usados apenas para o log no terminal (evita flood/spam repetitivo na sua tela de preta)
        pedidos_processados = set()
        pedidos_logados = set()
        ultimo_status_vazio = False

        # 🔁 LOOP PRINCIPAL (LOOP INFINITO)
        # Esse while True fica rodando "para sempre" de 5 em 5 segundos lendo a página.
        while True:
            try:
                # 🛡️ Proteção: Em painéis abertos muito tempo, é comum o acesso cair (Sessão Expirada).
                # Isso detecta queda da conta e reloga automaticamente antes de dar erro.
                if "login" in page.url:
                    print("⚠️ Sessão expirada, relogando...")
                    await fazer_login(page, email, senha)
                    await page.goto(URL_PEDIDOS)
                    lista = await esperar_lista_carregar(page)

                # Pega as "fileiras" filhas (cada pedido que aparece visualmente no HTML da lista)
                elementos = lista.locator("xpath=./div")

                # Conta quantos pedidos renderizaram neste exato momento na página
                total = await elementos.count()

                # Se a tela e a lista limpou (zeros pedidos aparecendo), avisamos:
                if total == 0:
                    if not ultimo_status_vazio:
                        print("📭 Nenhum pedido pendente aparecendo na plataforma. Voltando a aguardar...")
                        ultimo_status_vazio = True
                else:
                    ultimo_status_vazio = False

                # Passamos fazendo uma vistoria lendo um por um daqueles `total` de pedidos que ele achou na tela
                for i in range(total):
                    pedido = elementos.nth(i)

                    try:
                        # 📝 LEITURA DO PEDIDO DA TELA (Extração de Dados)
                        # Localizamos o item que contém o número diretamente via classe
                        numero_alvo = pedido.locator("span.request-number")
                        
                        # Se esse 'div' não tiver esse campo de número, ignoramos (pode ser um espaço em branco no HTML)
                        if await numero_alvo.count() == 0:
                            continue
                            
                        # text_content é instantâneo e não se importa se o elemento está 'visível', resolvendo o erro de timeout
                        numero_bruto = await numero_alvo.first.text_content()
                        
                        # Limpa o texto: Remove espaços e remove a "hashtag" se houver (Ex: "#4126" vira "4126")
                        numero = numero_bruto.replace("#", "").strip()

                        # Se esse pedido já foi processado e já clicamos antes, a gente 'pula/ignora' com o "continue"
                        if numero in pedidos_processados:
                            continue

                        # Apenas controle do print no seu terminal. Se acabamos de ver esse pedido, joga no log.
                        if numero not in pedidos_logados:
                            print(f"🔎 O painel web exibe o pedido da loja {bot_name} Numero: {numero}")
                            pedidos_logados.add(numero)

                        # ============================================================================================
                        # 🎯 PONTO DE COMPARAÇÃO E AÇÃO MÁXIMA DO BOT:
                        # Em vez de comparar com um único número de API, ele pergunta se o pedido da tela
                        # está anotado no 'caderninho' (fila_pedidos).
                        # ============================================================================================
                        if numero in fila_pedidos:
                            print(f"🔥 MATCH! Pedido da tela '{numero}' consta na nossa fila pendente do bot {bot_name}!")

                            # 🔘 AÇÃO:
                            # Localizamos o ícone exato e forçamos o clique com JavaScript (evaluate)
                            # Isso resolve o erro "Element is not visible" e garante que frameworks estritos leiam a ação
                            botao_icone = pedido.locator("div.set.row-status > button > i.material-icons.notranslate.despacho").first
                            await botao_icone.evaluate("el => el.click()")

                            # ESPERA o site processar o clique
                            await page.wait_for_timeout(2000)
                            
                            # SALVAR EVIDÊNCIA FÍSICA
                            #nome_arquivo = f"comprovante_{bot_name}_{numero}.png"
                            #await page.screenshot(path=nome_arquivo)

                            print(f"🚀 Pedido {numero} despachado com sucesso!")
                            print(f"📸 Cópia de segurança salva em anexo na pasta: {nome_arquivo}")
                            print("✅ Removendo pedido da fila e voltando a patrulhar!")

                            # Nós não usamos mais return aqui. O robô arranca a folha do caderninho e continua patrulhando!
                            fila_pedidos.remove(numero)
                            pedidos_processados.add(numero)

                    except Exception as e:
                        print(f"⚠️ Esse loop tropeçou ao tentar interagir ou ler o HTML de um pedido listado: {e}")

                # ⏱ INTERVALO DO LOOP
                # Quando acabamos de ler todos os `5` (exemplo) pedidos que estavam na tela,
                # congelamos o robô por 5.000 milissegundos (5 seg) antes de voltar lá em cima para rever a tela de novo.
                await page.wait_for_timeout(5000)

                # 🔄 ATENÇÃO AO REFRESH:
                # O painel que mostra "lista_esperando" atualiza os novos pedidos via AJAX na tela,
                # sem você recarregar a página (F5)?
                # SE SIM: O código está excelente assim (melhor performance).
                # SE NÃO: O bot precisa de apertar F5 também a cada X segundos. Caso sim, ative o delete os "#" abaixo:
                # await page.reload()
                # lista = await esperar_lista_carregar(page)

            except Exception as e:
                # Se algo bizarro como navegador fechar e etc acontecer, aguarda 2s e o While recomeça lá do topo.
                print(f"⚠️ Erro geral e grave do loop principal: {e}")
                await page.wait_for_timeout(2000)


# ==============================================================================
# ▶️ PONTO DE PARTIDA / EXECUÇÃO DO ARQUIVO PYTHON
# ==============================================================================
if __name__ == "__main__":
    # Teste local: substitua '9404' pelo número do pedido que deseja testar
    fila_pedidos.add("9404")
    asyncio.run(executar_automacao())
