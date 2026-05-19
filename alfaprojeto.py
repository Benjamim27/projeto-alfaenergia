import os
import requests
import datetime
import csv
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ==================================================================
# CONFIGURAÇÕES GLOBAIS (Lendo de forma segura da Nuvem)
# ==================================================================
TEU_EMAIL = os.environ.get("TEU_EMAIL")
TUA_SENHA_APP = os.environ.get("TUA_SENHA_APP")
DESTINATARIOS = [
    "pbenjamim2007@gmail.com", 
    "crybenjamim2007@gmail.com",
    "nunofalcao@alfaenergia.pt",
    "idalinapaiva550@zarco.pt"
]

FICHEIRO_HISTORICO = "historico_precos.json"

# ==================================================================
# FUNÇÕES DE SUPORTE
# ==================================================================
def obter_timestamp():
    return datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")

def carregar_historico():
    if os.path.exists(FICHEIRO_HISTORICO):
        try:
            with open(FICHEIRO_HISTORICO, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"{obter_timestamp()} ⚠️ Erro ao ler histórico: {e}")
    return {}

def salvar_historico(dados_mercados):
    historico = {}
    for merc in dados_mercados:
        historico[merc['nome']] = {
            'preco': merc['preco'],
            'entrega': merc['entrega'],
            'sessao': merc['sessao']  # Adicionado para manter sincronismo completo
        }
    try:
        with open(FICHEIRO_HISTORICO, 'w', encoding='utf-8') as f:
            json.dump(historico, f, indent=4, ensure_ascii=False)
        print(f"{obter_timestamp()} 💾 Estado dos mercados atualizado no histórico local.")
    except Exception as e:
        print(f"{obter_timestamp()} ❌ Erro ao salvar histórico: {e}")

def buscar_preco_por_mercado(mercado):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    data_hoje = datetime.date.today().strftime("%d/%m/%Y")
    url = f"https://www.mibgas.es/pt/ajax/table/daily-price/{mercado.lower()}/export?date={data_hoje}"
    
    try:
        resposta = requests.get(url, headers=headers, timeout=10)
        if resposta.status_code == 200:
            linhas = resposta.text.splitlines()
            leitor = csv.reader(linhas)
            for colunas in leitor:
                if len(colunas) >= 3 and "Diário" in colunas[0]:
                    preco_raw = colunas[2].strip()
                    if preco_raw == "-" or not preco_raw:
                        continue
                    
                    preco_limpo = float(preco_raw.replace('.', '').replace(',', '.'))
                    data_sessao = datetime.datetime.strptime(data_hoje, "%d/%m/%Y").date()
                    data_entrega = data_sessao + datetime.timedelta(days=1)
                    
                    return (data_sessao.strftime("%d/%m/%Y"), data_entrega.strftime("%d/%m/%Y"), preco_limpo)
    except Exception as e:
        print(f"{obter_timestamp()} ⚠️ Erro no mercado {mercado.upper()}: {e}")
        
    return None, None, None

def enviar_relatorio_email(dados_mercados):
    dia_entrega_atual = dados_mercados[0]['entrega'] if dados_mercados else "Atual"
    msg = MIMEMultipart('alternative')
    msg['From'] = f"ALFAENERGIA Analytics <{TEU_EMAIL}>"
    msg['To'] = ", ".join(DESTINATARIOS)
    msg['Subject'] = f"📊 ALFAENERGIA: Fecho de Preços MIBGAS - Entrega: {dia_entrega_atual}"

    corpo_html = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: 'Segoe UI', Calibri, Arial, sans-serif; color: #2D3748; margin: 0; padding: 30px; background-color: #F7FAFC;">
        <div style="max-width: 650px; margin: 0 auto; background-color: #FFFFFF; padding: 35px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05); border-top: 5px solid #004a99;">
            <div style="margin-bottom: 25px;">
                <h2 style="color: #004a99; margin: 0 0 8px 0; font-size: 18pt;">Dashboard Diário de Preços</h2>
                <p style="font-size: 10.5pt; color: #718096; margin: 0;">Relatório automatizado (MIBGAS).</p>
            </div>
            <hr style="border: 0; border-top: 1px solid #E2E8F0; margin: 20px 0;">
            <div style="margin: 25px 0; padding: 20px; border: 1px solid #E2E8F0; border-radius: 8px;">
                <h4 style="margin: 0 0 15px 0; color: #4A5568; font-size: 11pt; text-align: center; text-transform: uppercase;">Diferencial de Preço Visual (€/MWh)</h4>
    """
    for merc in dados_mercados:
        largura_calculada = min(int(merc['preco'] * 4.5), 450)
        cor_barra = "#28a745" if merc['nome'] == "VTP" else "#007bff"
        corpo_html += f"""
                <div style="margin-bottom: 12px;">
                    <div style="font-size: 9.5pt; font-weight: 600; margin-bottom: 4px;">{merc['nome']} ({merc['regiao']})</div>
                    <div style="background-color: #EDF2F7; border-radius: 4px; width: 100%; max-width: 450px;">
                        <div style="background-color: {cor_barra}; width: {largura_calculada}px; height: 26px; border-radius: 4px; color: #FFFFFF; font-weight: bold; font-size: 10pt; line-height: 26px; padding-left: 10px;">
                            {merc['preco']:.2f} €
                        </div>
                    </div>
                </div>
        """
    corpo_html += """
            </div>
            <table style="width: 100%; border-collapse: separate; border-spacing: 0; margin-top: 25px; font-size: 10.5pt; border: 1px solid #E2E8F0; border-radius: 6px; overflow: hidden;">
                <thead>
                    <tr style="background-color: #004a99; color: #FFFFFF; text-align: left;">
                        <th style="padding: 14px 16px;">Mercado / Polo</th>
                        <th style="padding: 14px 16px;">Sessão Fecho</th>
                        <th style="padding: 14px 16px; background-color: #218838;">Dia de Entrega</th>
                        <th style="padding: 14px 16px; text-align: right;">Preço Final</th>
                    </tr>
                </thead>
                <tbody>
    """
    for merc in dados_mercados:
        corpo_html += f"""
                    <tr style="background-color: #FFFFFF;">
                        <td style="padding: 14px 16px; font-weight: 600; border-bottom: 1px solid #E2E8F0;">{merc['nome']} ({merc['regiao']})</td>
                        <td style="padding: 14px 16px; color: #4A5568; border-bottom: 1px solid #E2E8F0;">{merc['sessao']}</td>
                        <td style="padding: 14px 16px; font-weight: 600; color: #1E7E34; border-bottom: 1px solid #E2E8F0;">{merc['entrega']}</td>
                        <td style="padding: 14px 16px; text-align: right; font-weight: 700; color: #004a99; border-bottom: 1px solid #E2E8F0;">{merc['preco']:.2f} EUR/MWh</td>
                    </tr>
        """
    corpo_html += """
                </tbody>
            </table>
            <div style="margin-top: 25px; padding-top: 15px; border-top: 1px solid #E2E8F0;">
                <p style="font-size: 10.5pt; color: #2D3748; margin: 25px 0 0 0;">
                    Melhores cumprimentos,<br>
                    <span style="color: #28a745; font-weight: 700;">Robô de Monitorização ALFAENERGIA</span>
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    msg.attach(MIMEText(corpo_html, 'html', 'utf-8'))
    try:
        servidor = smtplib.SMTP('smtp.gmail.com', 587)
        servidor.starttls()
        servidor.login(TEU_EMAIL, TUA_SENHA_APP)
        servidor.sendmail(TEU_EMAIL, DESTINATARIOS, msg.as_string())
        servidor.quit()
        print(f"{obter_timestamp()} 🎉 SUCESSO: Relatório gerencial enviado com sucesso!")
        return True
    except Exception as e:
        print(f"{obter_timestamp()} ❌ ERRO no subsistema de email: {e}")
        return False

if __name__ == "__main__":
    print(f"{obter_timestamp()} 🚀 Execução inicializada.")
    sessao_pvb, entrega_pvb, preco_pvb = buscar_preco_por_mercado("pvb")
    sessao_vtp, entrega_vtp, preco_vtp = buscar_preco_por_mercado("vtp")
    
    mercados_detetados = []
    if preco_pvb is not None:
        mercados_detetados.append({'nome': 'PVB', 'regiao': 'Espanha', 'preco': preco_pvb, 'sessao': sessao_pvb, 'entrega': entrega_pvb})
    if preco_vtp is not None:
        mercados_detetados.append({'nome': 'VTP', 'regiao': 'Portugal', 'preco': preco_vtp, 'sessao': sessao_vtp, 'entrega': entrega_vtp})
        
    if len(mercados_detetados) == 2:
        historico_anterior = carregar_historico()
        houve_alteracao = False
        
        for merc in mercados_detetados:
            nome = merc['nome']
            preco_atual = merc['preco']
            entrega_atual = merc['entrega']
            
            if nome not in historico_anterior:
                houve_alteracao = True
            else:
                preco_velho = historico_anterior[nome]['preco']
                entrega_velha = historico_anterior[nome]['entrega']
                if preco_atual != preco_velho or entrega_atual != entrega_velha:
                    houve_alteracao = True
        
        if houve_alteracao:
            # Primeiro salvamos o histórico localmente na máquina virtual do GitHub
            salvar_historico(mercados_detetados)
            # Depois disparamos o email corporativo
            enviar_relatorio_email(mercados_detetados)
        else:
            print(f"{obter_timestamp()} 💤 Preços já enviados anteriormente hoje. Nenhuma ação necessária.")
    else:
        print(f"{obter_timestamp()} 🛑 Os preços de hoje ainda não foram publicados pelo MIBGAS. A aguardar próxima execução...")
