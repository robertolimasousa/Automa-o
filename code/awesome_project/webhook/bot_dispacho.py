import asyncio
from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
)

# ==============================================================================
# 🔗 CONFIGURAÇÃO DE URLs DO SISTEMA
# ==============================================================================
URL_LOGIN = "https://cloud.machine.global/site/login"
URL_PEDIDOS = "https://cloud.machine.global/solicitacao/gestaoPedido"


# ==============================================================================
# 🧹 NORMALIZADOR DE NÚMEROS
# ==============================================================================
def normalizar_numero(valor):
    """
    Converte qualquer valor de pedido para string limpa.
    """
    if valor is None:
        return ""

    return (
        str(valor)
        .replace("#", "")
        .replace(" ", "")
        .replace("\n", "")
        .replace("\r", "")
        .strip()
    )


async def goto_com_retry(
    page, url, max_retries=3, timeout=60000, wait_until="domcontentloaded"
):
    """Navega para a URL com retries em caso de Timeout ou falha temporária."""
    context = getattr(page, "context", None)

    for tentativa in range(1, max_retries + 1):
        try:
            if page is None or page.is_closed():
                if context is None:
                    raise Exception("Página fechada e contexto indisponível")
                page = await context.new_page()

            print(f"🌐 Navegando para {url} (tentativa {tentativa}/{max_retries})")
            await page.goto(url, timeout=timeout, wait_until=wait_until)
            return page

        except PlaywrightTimeoutError as e:
            print(
                f"⚠️ Timeout ao carregar {url} ({e}). Tentativa {tentativa}/{max_retries}"
            )

            if tentativa == max_retries:
                raise

            await safe_wait_for_timeout(page, 2000)

            try:
                await page.reload(timeout=timeout, wait_until=wait_until)
            except Exception:
                pass

        except Exception as e:
            erro_texto = str(e)
            print(f"⚠️ Erro ao navegar para {url}: {erro_texto}")

            if tentativa == max_retries:
                raise

            if context and (
                "ERR_INSUFFICIENT_RESOURCES" in erro_texto
                or "insufficient resources" in erro_texto.lower()
            ):
                print("⚠️ Recriando página após erro de recursos insuficientes...")
                try:
                    if page is not None and not page.is_closed():
                        await page.close()
                except Exception:
                    pass
                page = await context.new_page()
            else:
                await safe_wait_for_timeout(page, 2000)

    raise Exception(f"❌ Impossível navegar para {url} após {max_retries} tentativas")


async def safe_wait_for_timeout(page, timeout):
    if page is None or page.is_closed():
        print("⚠️ Ignorando wait_for_timeout: página já está fechada.")
        return
    try:
        await page.wait_for_timeout(timeout)
    except Exception as e:
        if "Target page, context or browser has been closed" in str(e):
            print(
                "⚠️ wait_for_timeout não pôde ser executado porque a página foi fechada."
            )
            return
        raise


async def recover_page(page, context):
    if page is None or page.is_closed():
        if context is None:
            raise Exception("Página fechada e contexto indisponível")
        print("🔄 Página fechada. Criando uma nova página para continuar.")
        return await context.new_page()
    return page


# ==============================================================================
# 🔐 FUNÇÃO DE LOGIN
# ==============================================================================
async def fazer_login(page, email, senha):
    """
    Objetivo: Preencher os dados de usuário e senha na página de login e entrar no sistema.
    """

    print("🔐 Fazendo login...")

    # Força a ida para a tela de login
    page = await goto_com_retry(page, URL_LOGIN)

    # Tentamos fazer o login até 5 vezes
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

            await safe_wait_for_timeout(page, 500)

            await entrar_botao.click()

            try:
                # Espera o menu lateral aparecer após o login.
                # O carregamento pode ser mais lento, então usamos um timeout maior e confiamos no seletor.
                await page.wait_for_selector("#menu-lateral", timeout=30000)
                print("✅ Login realizado sucesso!")
                return

            except PlaywrightTimeoutError:
                if "login" not in page.url:
                    try:
                        await page.wait_for_selector("#menu-lateral", timeout=10000)
                        print("✅ Login realizado sucesso!")
                        return
                    except PlaywrightTimeoutError:
                        print(
                            "⚠️ Login parece ter ocorrido, mas '#menu-lateral' não apareceu. Continuando..."
                        )
                        return

                raise

            except Exception as e:
                # Se ocorrer outro erro, propagamos para permitir retry.
                raise e

        except Exception as e:
            print(f"⚠️ Erro login: {e}")

            if page.is_closed():
                raise Exception("❌ Página fechada durante o login") from e

            await page.wait_for_timeout(2000)
            await page.reload()
            await page.wait_for_load_state("domcontentloaded")

    raise Exception("❌ Falha no login")


# ==============================================================================
# 📦 FUNÇÃO DE ESPERA DA LISTA DE PEDIDOS
# ==============================================================================
async def esperar_lista_carregar(page):
    """
    Garante que a lista onde os pedidos chegam carregou.
    """

    lista = page.locator("#lista-pedidos_esperando")

    await lista.wait_for(state="attached", timeout=20000)

    return lista


# ==============================================================================
# 🤖 BOT PRINCIPAL - MONITORAMENTO DE PEDIDOS
# ==============================================================================

# 📝 FILA GLOBAL DE PEDIDOS
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

    print(f"🤖 Bot {bot_name} ativado (Modo 24/7): aguardando pedidos...")

    async with async_playwright() as p:

        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=True,
            slow_mo=100,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-extensions",
                "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding",
                "--disable-backgrounding-occluded-windows",
            ],
        )

        page = context.pages[0] if context.pages else await context.new_page()

        page = await goto_com_retry(page, URL_PEDIDOS)

        if "login" in page.url:
            await fazer_login(page, email, senha)
            page = await goto_com_retry(page, URL_PEDIDOS)

        lista = await esperar_lista_carregar(page)

        print("📦 Sistema pronto - loop iniciado...")

        pedidos_processados = set()
        pedidos_logados = set()
        ultimo_status_vazio = False

        # 🔁 LOOP PRINCIPAL
        while True:
            try:

                # 🛡️ Sessão expirada
                if "login" in page.url:
                    print("⚠️ Sessão expirada, relogando...")

                    await fazer_login(page, email, senha)

                    await page.goto(URL_PEDIDOS)

                    lista = await esperar_lista_carregar(page)

                # Lista de pedidos
                elementos = lista.locator("xpath=./div")

                total = await elementos.count()

                # Nenhum pedido
                if total == 0:

                    if not ultimo_status_vazio:
                        print("📭 Nenhum pedido pendente aparecendo na plataforma.")

                        ultimo_status_vazio = True

                else:
                    ultimo_status_vazio = False

                # Percorre pedidos
                for i in range(total):

                    pedido = elementos.nth(i)

                    try:

                        # Localiza número
                        numero_alvo = pedido.locator("span.request-number")

                        if await numero_alvo.count() == 0:
                            continue

                        numero_bruto = await numero_alvo.first.text_content()

                        # Normaliza número da tela
                        numero = normalizar_numero(numero_bruto)

                        # Ignora já processados
                        if numero in pedidos_processados:
                            continue

                        # Log visual
                        if numero not in pedidos_logados:
                            print(
                                f"🔎 Pedido encontrado na tela do bot {bot_name}: {numero}"
                            )

                            pedidos_logados.add(numero)

                        # ==============================================================================
                        # 🎯 NORMALIZA FILA
                        # ==============================================================================
                        fila_normalizada = {
                            normalizar_numero(item) for item in fila_pedidos
                        }

                        # ==============================================================================
                        # 🎯 MATCH
                        # ==============================================================================
                        if numero in fila_normalizada:

                            print(
                                f"🔥 MATCH! Pedido '{numero}' encontrado na fila do bot {bot_name}"
                            )

                            # Botão despacho
                            botao_icone = pedido.locator(
                                "div.set.row-status > button > i.material-icons.notranslate.despacho"
                            ).first

                            # Clique forçado
                            await botao_icone.evaluate("el => el.click()")

                            # Espera processamento
                            await safe_wait_for_timeout(page, 2000)

                            # Screenshot
                            nome_arquivo = f"comprovante_{bot_name}_{numero}.png"

                            await page.screenshot(path=nome_arquivo)

                            print(f"🚀 Pedido {numero} despachado com sucesso!")

                            print(f"📸 Comprovante salvo: {nome_arquivo}")

                            print("✅ Removendo pedido da fila...")

                            # Remove item original da fila
                            for item in list(fila_pedidos):

                                item_normalizado = normalizar_numero(item)

                                if item_normalizado == numero:
                                    fila_pedidos.remove(item)
                                    break

                            pedidos_processados.add(numero)

                    except Exception as e:
                        print(f"⚠️ Erro ao processar pedido listado: {e}")

                # Espera entre loops
                await safe_wait_for_timeout(page, 5000)

            except Exception as e:
                print(f"⚠️ Erro geral do loop principal: {e}")

                if page is None or page.is_closed():
                    try:
                        page = await recover_page(page, context)
                        page = await goto_com_retry(page, URL_PEDIDOS)
                        lista = await esperar_lista_carregar(page)
                        continue
                    except Exception as recovery_error:
                        print(f"⚠️ Falha ao recuperar sessão do bot: {recovery_error}")

                await safe_wait_for_timeout(page, 2000)


# ==============================================================================
# ▶️ EXECUÇÃO
# ==============================================================================
if __name__ == "__main__":

    # Teste local
    fila_pedidos.add("9404")

    asyncio.run(executar_automacao())
