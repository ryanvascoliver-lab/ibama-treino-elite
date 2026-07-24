# ==============================================================================
# 🛠️ CONFIGURAÇÕES E IMPORTAÇÕES (Setup Inicial do Sistema)
# ==============================================================================
import os
import json
import sqlite3
import random
import streamlit as st
from dotenv import load_dotenv
from google import genai

load_dotenv()
DB_NAME = "banco_ibama.db"

st.set_page_config(page_title="IBAMA - Treino de Elite", page_icon="🌲", layout="wide")


# ==============================================================================
# 🗄️ BANCO DE DADOS (Conexão Centralizada com o SQLite)
# ==============================================================================
def conectar_banco():
    """Abre e retorna a conexão com o banco local"""
    return sqlite3.connect(DB_NAME)


# ==============================================================================
# 🤖 GEMINI (IA - Mapeamento Inteligente do Relato de Estudo)
# ==============================================================================
def identificar_topico_via_chat(texto_usuario):
    """Usa a IA para mapear o texto livre do usuário para a Matéria/Tópico do Edital Mestre"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None, None

    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("SELECT materia, topico FROM editais")
    edital_completo = cursor.fetchall()
    conn.close()

    edital_fmt = "\n".join([f"- Matéria: {m} | Tópico: {t}" for m, t in edital_completo])

    prompt = f"""
    O estudante informou o seguinte resumo do que estudou hoje:
    "{texto_usuario}"

    Abaixo está a lista oficial de matérias e tópicos do Edital Mestre:
    {edital_fmt}

    Sua tarefa é identificar a MATÉRIA e o TÓPICO do edital que melhor correspondem ao que o estudante descreveu.
    Retorne APENAS um JSON estrito no seguinte formato:
    {{
      "materia": "Nome exato da matéria da lista",
      "topico": "Nome exato do tópico da lista"
    }}
    """

    client = genai.Client(api_key=api_key)
    modelos = ["gemini-2.5-flash", "gemini-1.5-flash"]
    
    for mod in modelos:
        try:
            res = client.models.generate_content(
                model=mod, contents=prompt, config={"response_mime_type": "application/json"}
            )
            dados = json.loads(res.text)
            return dados.get("materia"), dados.get("topico")
        except Exception:
            continue
    return None, None


# ==============================================================================
# 🤖 GEMINI (IA - Geração Automática de Questões Inéditas Cebraspe)
# ==============================================================================
def gerar_questoes_ia(materia, topico, qtd_necessaria):
    """Gera questões faltantes no formato Certo/Errado quando o lote precisa ser completado"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return

    client = genai.Client(api_key=api_key)
    prompt = f"""
    Gere exatamente {qtd_necessaria} questões inéditas no formato CERTO ou ERRADO (estilo Cebraspe).
    Matéria: {materia}
    Tópico: {topico}

    Retorne APENAS um JSON estrito no formato:
    [
      {{
        "item_inedito": "Texto do item para julgamento...",
        "gabarito_oficial": "Certo",
        "explicacao_gabarito": "Fundamentação jurídica/técnica detalhada..."
      }}
    ]
    """
    modelos = ["gemini-2.5-flash", "gemini-1.5-flash"]
    for mod in modelos:
        try:
            res = client.models.generate_content(
                model=mod, contents=prompt, config={"response_mime_type": "application/json"}
            )
            questoes_novas = json.loads(res.text)
            
            conn = conectar_banco()
            cursor = conn.cursor()
            for q in questoes_novas:
                cursor.execute("""
                    INSERT INTO questoes (materia, topico, topico_edital, item_inedito, gabarito_oficial, explicacao_gabarito, status_escopo)
                    VALUES (?, ?, ?, ?, ?, ?, 'Tema 2 - Fiscalizacao')
                """, (materia, topico, topico, q["item_inedito"], q["gabarito_oficial"], q["explicacao_gabarito"]))
            conn.commit()
            conn.close()
            break
        except Exception:
            continue


# ==============================================================================
# ✍️ GEMINI (IA - Geração e Correção de Redação Discursiva Cebraspe)
# ==============================================================================
def gerar_tema_redacao_ia(materia, topico):
    """Gera um tema de estudo de caso / discursiva no padrão Cebraspe (Max 30 linhas)"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Erro: Chave API não encontrada."

    client = genai.Client(api_key=api_key)
    prompt = f"""
    Você é um banca examinadora do Cebraspe para o concurso do IBAMA (Analista Ambiental).
    Crie uma proposta de PROVA DISCURSIVA (Redação) sobre o assunto:
    Matéria: {materia}
    Tópico: {topico}

    A proposta deve conter:
    1. Um texto motivador curto (situação hipotética de fiscalização ambiental ou cenário legal).
    2. O comando da questão solicitando um texto dissertativo de até 30 linhas.
    3. Exatamente 3 TÓPICOS OBRIGATÓRIOS que o candidato deve abordar, com a pontuação de cada um (totalizando 30 pontos).

    Retorne em Formato JSON estrito:
    {{
      "texto_motivador": "Texto...",
      "comando": "Considerando que o texto acima...",
      "topico_1": "1. [Descrição do item 1] (10 pontos)",
      "topico_2": "2. [Descrição do item 2] (10 pontos)",
      "topico_3": "3. [Descrição do item 3] (10 pontos)"
    }}
    """
    modelos = ["gemini-2.5-flash", "gemini-1.5-flash"]
    for mod in modelos:
        try:
            res = client.models.generate_content(
                model=mod, contents=prompt, config={"response_mime_type": "application/json"}
            )
            return json.loads(res.text)
        except Exception:
            continue
    return None

def corrigir_redacao_ia(proposta_json, texto_aluno):
    """Avalia o texto do aluno segundo os critérios oficiais de correção Cebraspe"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Erro: Chave API não encontrada."

    client = genai.Client(api_key=api_key)
    prompt = f"""
    Você é o examinador chefe da banca Cebraspe corrigindo a prova discursiva de um candidato ao IBAMA.
    
    PROPOSTA DA REDAÇÃO:
    Texto Motivador: {proposta_json.get('texto_motivador')}
    Comando: {proposta_json.get('comando')}
    Tópico 1: {proposta_json.get('topico_1')}
    Tópico 2: {proposta_json.get('topico_2')}
    Tópico 3: {proposta_json.get('topico_3')}

    TEXTO DO CANDIDATO:
    "{texto_aluno}"

    Avalie o texto segundo a fórmula oficial do Cebraspe:
    Nota Final = Nota de Conteúdo (NC) - (Desvios Gramaticais x 0.5)

    Retorne a correção em JSON estrito no seguinte formato:
    {{
      "nota_conteudo": 28.5,
      "desvios_gramaticais": 2,
      "nota_final": 27.5,
      "avaliacao_topico_1": "Análise detalhada do cumprimento do tópico 1...",
      "avaliacao_topico_2": "Análise detalhada do cumprimento do tópico 2...",
      "avaliacao_topico_3": "Análise detalhada do cumprimento do tópico 3...",
      "apontamento_erros": "Aponta erros de concordância, regência ou pontuação se houver...",
      "sugestão_melhoria": "Como o candidato poderia reescrever para gabaritar a nota máxima."
    }}
    """
    modelos = ["gemini-2.5-flash", "gemini-1.5-flash"]
    for mod in modelos:
        try:
            res = client.models.generate_content(
                model=mod, contents=prompt, config={"response_mime_type": "application/json"}
            )
            return json.loads(res.text)
        except Exception:
            continue
    return None


# ==============================================================================
# 🔍 FILTRO & CÁLCULO (Busca Direta por Vínculo do Edital Mestre)
# ==============================================================================
def calcular_dominio_real_topico(topico):
    """FILTRO DIRETO: Puxa a contagem do banco pela coluna vinculada topico_edital"""
    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) FROM questoes 
        WHERE topico_edital = ? AND status_escopo != 'Fora do Escopo'
    """, (topico,))
    total_banco = cursor.fetchone()[0] or 0

    try:
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT questao_id) as resolvidas_unicas,
                COUNT(DISTINCT CASE WHEN acertou = 1 THEN questao_id END) as acertos_unicos,
                COUNT(CASE WHEN acertou = 0 THEN 1 END) as total_erros
            FROM respostas 
            WHERE topico = ? OR topico_edital = ?
        """, (topico, topico))
        row_resp = cursor.fetchone()
        resolvidas_unicas = row_resp[0] if row_resp else 0
        acertos_unicos = row_resp[1] if row_resp else 0
        erros_pendentes = row_resp[2] if row_resp else 0
    except Exception:
        resolvidas_unicas, acertos_unicos, erros_pendentes = 0, 0, 0

    conn.close()

    aproveitamento = (acertos_unicos / resolvidas_unicas * 100) if resolvidas_unicas > 0 else 0.0
    dominio_real = (acertos_unicos / total_banco * 100) if total_banco > 0 else 0.0

    return {
        "total_banco": total_banco,
        "resolvidas_unicas": resolvidas_unicas,
        "acertos_unicos": acertos_unicos,
        "erros_pendentes": erros_pendentes,
        "aproveitamento": round(aproveitamento, 1),
        "dominio_real": round(dominio_real, 1)
    }


# ==============================================================================
# 🎨 LAYOUT & NAVEGAÇÃO (Menu Lateral)
# ==============================================================================
st.sidebar.title("🌲 Preparatório IBAMA")
st.sidebar.caption("Treino de Elite - Edital Mestre")
opcao = st.sidebar.radio("Menu", [
    "💬 Chat de Estudo Diário",
    "📅 Simulado da Semana",
    "✍️ Oficina de Redação Discursiva",
    "📊 Porcentagem de Domínio",
    "📚 Super Edital"
])


# ==============================================================================
# 💻 INTERFACE 1: CHAT DE ESTUDO DIÁRIO
# ==============================================================================
if opcao == "💬 Chat de Estudo Diário":
    st.header("💬 O que você estudou hoje?")
    st.write("Escreva com suas palavras o conteúdo estudado. A IA vai identificar o tópico do edital e preparar 10 questões na hora.")

    estudo_texto = st.text_input(
        "Digite aqui:", 
        placeholder="Ex: Hoje estudei crimes contra a fauna e processo sancionador ambiental..."
    )

    if st.button("🚀 Processar e Gerar 10 Exercícios"):
        if not estudo_texto.strip():
            st.warning("Por favor, digite o que você estudou antes de enviar!")
        else:
            with st.spinner("🤖 GEMINI analisando seu relato e buscando o tópico no Edital Mestre..."):
                materia_id, topico_id = identificar_topico_via_chat(estudo_texto)

            if topico_id:
                conn = conectar_banco()
                cursor = conn.cursor()
                cursor.execute("UPDATE editais SET estudado_na_semana = 1 WHERE topico = ?", (topico_id,))
                conn.commit()
                
                cursor.execute("SELECT id FROM questoes WHERE topico_edital = ? AND status_escopo != 'Fora do Escopo'", (topico_id,))
                q_existentes = cursor.fetchall()
                conn.close()

                qtd_atual = len(q_existentes)
                if qtd_atual < 10:
                    with st.spinner(f"🤖 GEMINI gerando {10 - qtd_atual} questões inéditas para fechar o lote..."):
                        gerar_questoes_ia(materia_id, topico_id, 10 - qtd_atual)

                st.session_state["treino_atual"] = {
                    "materia": materia_id,
                    "topico": topico_id
                }
                st.success(f"🎯 Mapeado para: **{materia_id}** ➔ **{topico_id}**")
            else:
                st.error("Não foi possível associar seu texto a um tópico do edital. Tente ser mais específico!")

    if "treino_atual" in st.session_state:
        info_t = st.session_state["treino_atual"]
        st.markdown("---")
        st.subheader(f"📝 10 Exercícios do Tópico: {info_t['topico']}")

        conn = conectar_banco()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, item_inedito, gabarito_oficial, explicacao_gabarito 
            FROM questoes 
            WHERE topico_edital = ? AND status_escopo != 'Fora do Escopo'
            LIMIT 10
        """, (info_t["topico"],))
        questoes = cursor.fetchall()
        conn.close()

        respostas_usuario = {}
        for idx, q in enumerate(questoes, 1):
            q_id, item, gabarito, explicacao = q
            st.markdown(f"**Questão {idx}:** {item}")
            respostas_usuario[q_id] = st.radio(f"Julgamento Q{idx}:", ["Certo", "Errado"], key=f"q_{q_id}", index=None)
            st.markdown("")

        if st.button("📌 Finalizar Treino e Registrar Desempenho"):
            acertos = 0
            conn = conectar_banco()
            cursor = conn.cursor()
            
            for q_id, item, gabarito, explicacao in questoes:
                resp = respostas_usuario.get(q_id)
                acertou = 1 if resp == gabarito else 0
                if acertou:
                    acertos += 1
                cursor.execute("""
                    INSERT INTO respostas (questao_id, materia, topico, acertou)
                    VALUES (?, ?, ?, ?)
                """, (q_id, info_t["materia"], info_t["topico"], acertou))
            
            cursor.execute("UPDATE editais SET estudado_na_semana = 1 WHERE topico = ?", (info_t["topico"],))
            conn.commit()
            conn.close()

            st.balloons()
            st.success(f"Treino Concluído! Você acertou **{acertos}/10** ({acertos * 10}%).")
            st.info("Sua porcentagem de domínio foi atualizada no painel de desempenho!")


# ==============================================================================
# 💻 INTERFACE 2: SIMULADO DA SEMANA (Acesso Permanente)
# ==============================================================================
elif opcao == "📅 Simulado da Semana":
    st.header("📅 Simulado Cumulativo dos Conteúdos Estudados")
    st.write("Monte e resolva simulados em qualquer momento com base nos assuntos que você estudou nesta semana.")

    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("SELECT materia, topico FROM editais WHERE estudado_na_semana = 1")
    topicos_semana = cursor.fetchall()
    conn.close()

    if not topicos_semana:
        st.info("Nenhum tópico marcado como estudado na semana ainda. Registre seu estudo no Chat Diário primeiro!")
    else:
        st.subheader(f"Tópicos no Acumulado Semanal ({len(topicos_semana)}):")
        for m, t in topicos_semana:
            st.write(f"• **{m}** ➔ {t}")

        st.markdown("---")
        c_sim1, c_sim2 = st.columns([2, 1])

        with c_sim1:
            if st.button("🚀 Gerar e Resolver Simulado Agora"):
                topicos_nomes = [t[1] for t in topicos_semana]
                placeholders = ",".join(["?"] * len(topicos_nomes))
                
                conn = conectar_banco()
                cursor = conn.cursor()
                cursor.execute(f"""
                    SELECT id, materia, topico_edital, item_inedito, gabarito_oficial, explicacao_gabarito
                    FROM questoes
                    WHERE topico_edital IN ({placeholders}) AND status_escopo != 'Fora do Escopo'
                    ORDER BY RANDOM()
                    LIMIT 20
                """, topicos_nomes)
                st.session_state["questoes_simulado_semanal"] = cursor.fetchall()
                conn.close()

        with c_sim2:
            if st.button("🔄 Reiniciar Ciclo Semanal (Limpar Fila)"):
                conn = conectar_banco()
                cursor = conn.cursor()
                cursor.execute("UPDATE editais SET estudado_na_semana = 0")
                conn.commit()
                conn.close()
                if "questoes_simulado_semanal" in st.session_state:
                    del st.session_state["questoes_simulado_semanal"]
                st.success("Ciclo Semanal reiniciado!")
                st.rerun()

    # EXECUÇÃO DO SIMULADO GERADO
    if "questoes_simulado_semanal" in st.session_state:
        questoes_sim = st.session_state["questoes_simulado_semanal"]
        st.markdown("---")
        st.subheader(f"📝 Simulado da Semana - {len(questoes_sim)} Questões Sorteadas")

        respostas_simulados = {}
        for idx, q in enumerate(questoes_sim, 1):
            q_id, mat, top, item, gab, expl = q
            st.markdown(f"**Q{idx} [{mat}]:** {item}")
            respostas_simulados[q_id] = st.radio(f"Sua resposta Q{idx}:", ["Certo", "Errado"], key=f"sim_{q_id}", index=None)
            st.markdown("")

        if st.button("📌 Finalizar Simulado Semanal"):
            acertos = 0
            conn = conectar_banco()
            cursor = conn.cursor()

            for q in questoes_sim:
                q_id, mat, top, item, gab, expl = q
                resp = respostas_simulados.get(q_id)
                acertou = 1 if resp == gab else 0
                if acertou:
                    acertos += 1
                cursor.execute("""
                    INSERT INTO respostas (questao_id, materia, topico, acertou)
                    VALUES (?, ?, ?, ?)
                """, (q_id, mat, top, acertou))

            conn.commit()
            conn.close()

            taxa = round((acertos / len(questoes_sim)) * 100, 1)
            st.balloons()
            st.success(f"Simulado Concluído! Você acertou **{acertos} de {len(questoes_sim)}** ({taxa}% de aproveitamento).")


# ==============================================================================
# 💻 INTERFACE 3: OFICINA DE REDAÇÃO DISCURSIVA (Inédito Cebraspe)
# ==============================================================================
elif opcao == "✍️ Oficina de Redação Discursiva":
    st.header("✍️ Oficina de Redação Discursiva (Padrão Cebraspe)")
    st.caption("Treine a prova discursiva com temas inéditos do IBAMA e receba a correção oficial por IA baseada no espelho do Cebraspe.")

    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT materia FROM editais")
    materias_red = [m[0] for m in cursor.fetchall()]

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        mat_sel = st.selectbox("Selecione a Matéria do Tema:", materias_red)
    with col_m2:
        cursor.execute("SELECT topico FROM editais WHERE materia = ?", (mat_sel,))
        topicos_red = [t[0] for t in cursor.fetchall()]
        top_sel = st.selectbox("Selecione o Tópico Específico:", topicos_red)

    conn.close()

    if st.button("🎯 Gerar Proposta de Redação Inédita"):
        with st.spinner("🤖 GEMINI elaborando estudo de caso e espelho de avaliação..."):
            proposta = gerar_tema_redacao_ia(mat_sel, top_sel)
            if proposta:
                st.session_state["proposta_redacao_atual"] = proposta

    # EXIBIÇÃO DA PROPOSTA E ÁREA DE TEXTO
    if "proposta_redacao_atual" in st.session_state:
        p = st.session_state["proposta_redacao_atual"]
        st.markdown("---")
        st.subheader("📋 Proposta da Prova Discursiva")
        
        st.info(f"**Texto Motivador:**\n{p.get('texto_motivador')}")
        st.warning(f"**Comando da Questão:**\n{p.get('comando')}")
        
        st.markdown("**Tópicos Obrigatórios a Abordar:**")
        st.write(f"• {p.get('topico_1')}")
        st.write(f"• {p.get('topico_2')}")
        st.write(f"• {p.get('topico_3')}")

        st.markdown("---")
        st.subheader("✏️ Sua Resposta (Até 30 Linhas):")
        texto_redacao = st.text_area("Digite ou cole seu texto aqui:", height=250, placeholder="Em relação ao tema proposto, cabe destacar que...")

        if st.button("📊 Enviar Redação para Correção pelo Cebraspe IA"):
            if len(texto_redacao.strip()) < 50:
                st.warning("Escreva um texto um pouco mais completo antes de enviar para correção!")
            else:
                with st.spinner("🤖 Examinador Cebraspe corrigindo conteúdo, estrutura e desvios gramaticais..."):
                    correcao = corrigir_redacao_ia(p, texto_redacao)

                if correcao:
                    st.markdown("---")
                    st.header("🏆 Espelho Oficial de Correção")

                    c_nc1, c_nc2, c_nc3 = st.columns(3)
                    c_nc1.metric("Nota de Conteúdo (NC)", f"{correcao.get('nota_conteudo')}/30")
                    c_nc2.metric("Desvios Gramaticais", correcao.get('desvios_gramaticais'))
                    c_nc3.metric("NOTA FINAL CEBRASPE", f"{correcao.get('nota_final')}/30")

                    st.markdown("### 🔍 Avaliação por Tópico:")
                    st.write(f"**Item 1:** {correcao.get('avaliacao_topico_1')}")
                    st.write(f"**Item 2:** {correcao.get('avaliacao_topico_2')}")
                    st.write(f"**Item 3:** {correcao.get('avaliacao_topico_3')}")

                    st.markdown("### ⚠️ Desvios e Gramática:")
                    st.write(correcao.get('apontamento_erros'))

                    st.markdown("### 💡 Sugestão do Examinador para Gabaritar:")
                    st.success(correcao.get('sugestão_melhoria'))


# ==============================================================================
# 💻 INTERFACE 4: PORCENTAGEM DE DOMÍNIO
# ==============================================================================
elif opcao == "📊 Porcentagem de Domínio":
    st.header("📊 Nível de Domínio Real por Matéria e Tópico")
    st.caption("O Domínio Real calcula seus acertos únicos sobre o **TOTAL ABSOLUTO** de questões existentes no banco para cada assunto do Edital Mestre.")

    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT materia FROM editais")
    materias = [m[0] for m in cursor.fetchall()]

    for mat in materias:
        cursor.execute("SELECT topico FROM editais WHERE materia = ?", (mat,))
        topicos = [t[0] for t in cursor.fetchall()]
        
        dados_topicos = [calcular_dominio_real_topico(t) for t in topicos]
        
        if dados_topicos:
            media_materia = round(sum(d["dominio_real"] for d in dados_topicos) / len(dados_topicos), 1)
        else:
            media_materia = 0.0

        with st.expander(f"📚 {mat} — **{media_materia}% de Domínio Real Geral**"):
            st.progress(min(int(media_materia), 100))
            
            for top, d in zip(topicos, dados_topicos):
                st.markdown(f"#### 🔹 {top}")
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Questões no Banco", d["total_banco"])
                c2.metric("Resolvidas Únicas", d["resolvidas_unicas"])
                c3.metric("Aproveitamento", f"{d['aproveitamento']}%")
                c4.metric("Domínio Real", f"{d['dominio_real']}%")

                if d["dominio_real"] >= 85:
                    status = "🟢 MAESTRIA ATINGIDA"
                elif d["dominio_real"] >= 40:
                    status = "🟡 EM EVOLUÇÃO"
                else:
                    status = "🔴 INICIANTE / REVISAR"
                    
                st.write(f"**Status:** {status}")
                st.progress(min(int(d["dominio_real"]), 100))
                st.divider()

    conn.close()


# ==============================================================================
# 💻 INTERFACE 5: SUPER EDITAL
# ==============================================================================
elif opcao == "📚 Super Edital":
    st.header("📚 Estrutura Completa do Edital Mestre")
    
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("SELECT modulo, materia, topico, estudado_na_semana FROM editais")
    itens = cursor.fetchall()
    conn.close()

    for mod, mat, top, est in itens:
        status = "✅ Estudado na Semana" if est else "⚪ Pendente"
        st.write(f"[{status}] **{mat}** ➔ {top}")