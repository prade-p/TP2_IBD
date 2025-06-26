import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3
import numpy as np

# Configuração da página
st.set_page_config(
    page_title="SISAGUA - Dashboard",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 600;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        padding: 1.5rem;
        background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
        border-radius: 12px;
        border: 1px solid #2563eb;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .metric-container {
        background: white;
        padding: 1.2rem;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        margin: 0.5rem 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .section-header {
        color: #1e40af;
        border-bottom: 2px solid #dbeafe;
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem;
        font-weight: 500;
    }
    .sidebar .sidebar-content {
        background-color: #f1f5f9;
    }
    .kpi-card {
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #0284c7;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Conectar ao banco de dados
@st.cache_resource
def init_connection():
    try:
        return sqlite3.connect('sisagua.db', check_same_thread=False)
    except Exception as e:
        st.error(f"Erro ao conectar com o banco: {e}")
        st.stop()

conn = init_connection()

@st.cache_data
def run_query(query):
    try:
        return pd.read_sql_query(query, conn)
    except Exception as e:
        st.error(f"Erro na consulta: {e}")
        return pd.DataFrame()

# Consultas SQL atualizadas
def get_consultas():
    return {
        'etas_tecnologia': '''
        SELECT 
            tipo_filtracao as "Tecnologia de Tratamento",
            COUNT(*) as "Qtd ETAs",
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM ETA), 2) as "Percentual"
        FROM ETA 
        WHERE tipo_filtracao IS NOT NULL AND tipo_filtracao != ''
        GROUP BY tipo_filtracao
        ORDER BY COUNT(*) DESC
        ''',
        
        'parametros_qualidade': '''
        SELECT 
            nome_parametro as "Parâmetro de Qualidade",
            unidade_medida as "Unidade",
            CASE 
                WHEN nome_parametro LIKE '%Turbidez%' THEN 'Aspecto Físico'
                WHEN nome_parametro LIKE '%Cor%' THEN 'Aspecto Físico'
                WHEN nome_parametro LIKE '%Cloro%' THEN 'Desinfecção'
                WHEN nome_parametro LIKE '%pH%' THEN 'Equilíbrio Químico'
                WHEN nome_parametro LIKE '%Fluoreto%' THEN 'Saúde Pública'
                WHEN nome_parametro LIKE '%coli%' THEN 'Segurança Microbiológica'
                WHEN nome_parametro LIKE '%Coliforme%' THEN 'Segurança Microbiológica'
                ELSE 'Outros Indicadores'
            END as "Finalidade do Monitoramento"
        FROM Parametro 
        WHERE nome_parametro IS NOT NULL AND nome_parametro != ''
        ORDER BY 
            CASE 
                WHEN nome_parametro LIKE '%Turbidez%' THEN 1
                WHEN nome_parametro LIKE '%Cloro%' THEN 2
                WHEN nome_parametro LIKE '%pH%' THEN 3
                WHEN nome_parametro LIKE '%coli%' THEN 4
                ELSE 5
            END,
            nome_parametro
        ''',
        
        'etas_estado': '''
        SELECT 
            e.uf as "UF",
            e.nome_estado as "Estado",
            COUNT(DISTINCT eta.id_eta) as "Total ETAs",
            COUNT(DISTINCT mun.id_municipio) as "Municípios com ETA",
            ROUND(1.0 * COUNT(DISTINCT eta.id_eta) / COUNT(DISTINCT mun.id_municipio), 2) as "ETAs por Município"
        FROM Estado e
        INNER JOIN Municipio mun ON e.id_estado = mun.id_estado
        INNER JOIN ETA eta ON mun.id_municipio = eta.id_municipio
        GROUP BY e.uf, e.nome_estado
        HAVING COUNT(DISTINCT eta.id_eta) > 0
        ORDER BY COUNT(DISTINCT eta.id_eta) DESC
        ''',
        
        'medicoes_ponto': '''
        SELECT 
            pm.tipo_ponto as "Tipo",
            pm.nome_ponto as "Ponto de Monitoramento",
            COUNT(m.id_medicao) as "Total Medições",
            ROUND(COUNT(m.id_medicao) * 100.0 / (SELECT COUNT(*) FROM Medicao), 2) as "% do Total"
        FROM Ponto_Monitoramento pm
        INNER JOIN Medicao m ON pm.id_ponto = m.id_ponto
        GROUP BY pm.tipo_ponto, pm.nome_ponto
        ORDER BY COUNT(m.id_medicao) DESC
        ''',
        
        'parametros_categoria': '''
        SELECT 
            p.categoria_parametro as "Categoria",
            p.nome_parametro as "Parâmetro",
            COUNT(m.id_medicao) as "Total Medições",
            ROUND(COUNT(m.id_medicao) * 100.0 / (SELECT COUNT(*) FROM Medicao), 2) as "% do Total"
        FROM Parametro p
        INNER JOIN Medicao m ON p.id_parametro = m.id_parametro
        GROUP BY p.categoria_parametro, p.nome_parametro
        ORDER BY p.categoria_parametro, COUNT(m.id_medicao) DESC
        ''',
        
        'analise_geografica': '''
        SELECT 
            r.nome_regiao as "Região",
            e.uf as "UF",
            COUNT(DISTINCT mun.id_municipio) as "Municípios",
            COUNT(DISTINCT eta.id_eta) as "ETAs Ativas",
            COUNT(med.id_medicao) as "Total Medições",
            ROUND(COUNT(med.id_medicao) * 1.0 / COUNT(DISTINCT eta.id_eta), 0) as "Medições/ETA"
        FROM Regiao r
        INNER JOIN Estado e ON r.id_regiao = e.id_regiao
        INNER JOIN Municipio mun ON e.id_estado = mun.id_estado
        INNER JOIN ETA eta ON mun.id_municipio = eta.id_municipio
        INNER JOIN Medicao med ON eta.id_eta = med.id_eta
        GROUP BY r.nome_regiao, e.uf
        HAVING COUNT(med.id_medicao) > 0
        ORDER BY COUNT(med.id_medicao) DESC
        ''',
        
        'performance_instituicao': '''
        SELECT 
            i.nome_instituicao as "Instituição",
            i.tipo_instituicao as "Tipo",
            COUNT(DISTINCT eta.id_eta) as "ETAs",
            COUNT(DISTINCT p.id_parametro) as "Parâmetros",
            COUNT(med.id_medicao) as "Medições",
            ROUND(COUNT(med.id_medicao) * 1.0 / COUNT(DISTINCT eta.id_eta), 0) as "Med/ETA"
        FROM Instituicao i
        INNER JOIN Escritorio_Regional er ON i.id_instituicao = er.id_instituicao
        INNER JOIN ETA eta ON er.id_escritorio = eta.id_escritorio
        INNER JOIN Medicao med ON eta.id_eta = med.id_eta
        INNER JOIN Parametro p ON med.id_parametro = p.id_parametro
        GROUP BY i.nome_instituicao, i.tipo_instituicao
        HAVING COUNT(med.id_medicao) > 1000
        ORDER BY COUNT(DISTINCT eta.id_eta) DESC
        ''',
        
        'analise_filtracao': '''
        WITH total_analises AS (
            SELECT
                eta.tipo_filtracao,
                p.nome_parametro,
                SUM(med.valor_medido) AS total_analises_parametro
            FROM ETA eta
            INNER JOIN Medicao med ON eta.id_eta = med.id_eta
            INNER JOIN Parametro p ON med.id_parametro = p.id_parametro
            INNER JOIN Campo c ON med.id_campo = c.id_campo
            WHERE (
                (p.nome_parametro = 'Cloro Residual Livre (mg/L)' AND c.nome_campo IN (
                    'Número de dados >= 2,0 mg/L e <= 5,0mg/L',
                    'Número de dados < 0,2 mg/L',
                    'Número de dados > 5,0 mg/L'
                ))
                OR
                (p.nome_parametro = 'Cor (uH)' AND c.nome_campo IN (
                    'Número de dados <= 15,0 uH',
                    'Número de dados > 15,0 uH'
                ))
                OR
                (p.nome_parametro = 'pH' AND c.nome_campo IN (
                    'Número de dados >= 6,0 e <= 9,0',
                    'Número de dados < 6,0',
                    'Número de dados > 9,0'
                ))
            )
            GROUP BY eta.tipo_filtracao, p.nome_parametro
        )
        SELECT
            eta.tipo_filtracao AS "Tipo Filtração",
            p.nome_parametro AS "Parâmetro",
            c.nome_campo AS "Faixa de Valores",
            SUM(med.valor_medido) AS "Análises",
            COUNT(DISTINCT eta.id_eta) AS "ETAs",
            ROUND(SUM(med.valor_medido) * 100.0 / ta.total_analises_parametro, 2) AS "Porcentagem"
        FROM ETA eta
        INNER JOIN Medicao med ON eta.id_eta = med.id_eta
        INNER JOIN Parametro p ON med.id_parametro = p.id_parametro
        INNER JOIN Campo c ON med.id_campo = c.id_campo
        INNER JOIN total_analises ta ON
            ta.tipo_filtracao = eta.tipo_filtracao AND
            ta.nome_parametro = p.nome_parametro
        WHERE (
            (p.nome_parametro = 'Cloro Residual Livre (mg/L)' AND c.nome_campo IN (
                'Número de dados >= 2,0 mg/L e <= 5,0mg/L',
                'Número de dados < 0,2 mg/L',
                'Número de dados > 5,0 mg/L'
            ))
            OR
            (p.nome_parametro = 'Cor (uH)' AND c.nome_campo IN (
                'Número de dados <= 15,0 uH',
                'Número de dados > 15,0 uH'
            ))
            OR
            (p.nome_parametro = 'pH' AND c.nome_campo IN (
                'Número de dados >= 6,0 e <= 9,0',
                'Número de dados < 6,0',
                'Número de dados > 9,0'
            ))
        )
        GROUP BY eta.tipo_filtracao, p.nome_parametro, c.nome_campo, ta.total_analises_parametro
        HAVING COUNT(med.id_medicao) >= 10
        ORDER BY eta.tipo_filtracao, p.nome_parametro, c.nome_campo DESC
        ''',
        
        'ranking_estados': '''
        SELECT 
            e.nome_estado as "Estado",
            COUNT(DISTINCT eta.id_eta) as "ETAs",
            COUNT(DISTINCT p.id_parametro) as "Parâmetros",
            COUNT(med.id_medicao) as "Medições"
        FROM Estado e
        INNER JOIN Municipio mun ON e.id_estado = mun.id_estado
        INNER JOIN ETA eta ON mun.id_municipio = eta.id_municipio
        INNER JOIN Medicao med ON eta.id_eta = med.id_eta
        INNER JOIN Parametro p ON med.id_parametro = p.id_parametro
        GROUP BY e.nome_estado
        HAVING COUNT(DISTINCT eta.id_eta) >= 5
        ORDER BY COUNT(DISTINCT p.id_parametro) DESC, COUNT(med.id_medicao) DESC
        ''',
        
        # NOVA CONSULTA 4.1: Evolução temporal
        'evolucao_temporal': '''
        SELECT 
            r.nome_regiao as "Região",
            med.mes_referencia as "Mês",
            COUNT(med.id_medicao) as "Total de Registros",
            COUNT(DISTINCT eta.id_eta) as "ETAs Ativas",
            COUNT(DISTINCT p.id_parametro) as "Parâmetros Distintos",
            ROUND(COUNT(med.id_medicao) * 1.0 / COUNT(DISTINCT eta.id_eta), 1) as "Intensidade (Reg/ETA)",
            ROUND(COUNT(DISTINCT p.id_parametro) * 1.0 / COUNT(DISTINCT eta.id_eta), 2) as "Diversidade (Par/ETA)",
            CASE 
                WHEN med.mes_referencia <= 2 THEN 'Início do Ano'
                WHEN med.mes_referencia <= 4 THEN 'Meio do Ano'
                ELSE 'Segundo Semestre'
            END as "Período"
        FROM Regiao r
        INNER JOIN Estado e ON r.id_regiao = e.id_regiao
        INNER JOIN Municipio mun ON e.id_estado = mun.id_estado
        INNER JOIN ETA eta ON mun.id_municipio = eta.id_municipio
        INNER JOIN Medicao med ON eta.id_eta = med.id_eta
        INNER JOIN Parametro p ON med.id_parametro = p.id_parametro
        WHERE med.ano_referencia = 2025
        GROUP BY r.nome_regiao, med.mes_referencia
        HAVING COUNT(med.id_medicao) >= 100
        ORDER BY r.nome_regiao, med.mes_referencia
        ''',
        
        'metricas_gerais': '''
        SELECT 
            'Estados Monitorados' as tipo, COUNT(DISTINCT e.nome_estado) as valor 
        FROM Estado e
        INNER JOIN Municipio m ON e.id_estado = m.id_estado
        INNER JOIN ETA eta ON m.id_municipio = eta.id_municipio
        UNION ALL
        SELECT 'ETAs Ativas', COUNT(*) FROM ETA
        UNION ALL  
        SELECT 'Total de Medições', COUNT(*) FROM Medicao
        UNION ALL
        SELECT 'Parâmetros Monitorados', COUNT(*) FROM Parametro
        UNION ALL
        SELECT 'Municípios Atendidos', COUNT(DISTINCT m.id_municipio) 
        FROM Municipio m 
        INNER JOIN ETA eta ON m.id_municipio = eta.id_municipio
        '''
    }

# Header principal
st.markdown('<h1 class="main-header">💧 SISAGUA - Monitoramento da Qualidade da Água</h1>', unsafe_allow_html=True)

# Sidebar
st.sidebar.title("🧭 Navegação")
page = st.sidebar.selectbox(
    "Escolha uma seção:",
    [
        "📊 Visão Geral",
        "🏭 Infraestrutura", 
        "🌍 Distribuição Territorial",
        "🏢 Análise Institucional", 
        "📈 Indicadores de Qualidade",
        "⏰ Evolução Temporal"  # NOVA PÁGINA
    ]
)

consultas = get_consultas()

# Função auxiliar para criar gráficos com estilo consistente
def create_styled_chart(fig, title, height=450):
    fig.update_layout(
        title=title,
        height=height,
        font=dict(size=12),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig

# Páginas
if page == "📊 Visão Geral":
    st.markdown('<h2 class="section-header">Panorama do Sistema SISAGUA</h2>', unsafe_allow_html=True)
    
    # Métricas principais
    try:
        df_metricas = run_query(consultas['metricas_gerais'])
        
        if not df_metricas.empty:
            col1, col2, col3, col4, col5 = st.columns(5)
            
            metrics_cols = [col1, col2, col3, col4, col5]
            
            for i, (_, row) in enumerate(df_metricas.iterrows()):
                if i < len(metrics_cols):
                    with metrics_cols[i]:
                        st.metric(row['tipo'], f"{row['valor']:,}")
                        st.markdown('</div>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Erro ao carregar métricas: {e}")
    
    # Gráficos principais
    col1, col2 = st.columns(2)
    
    with col1:
        try:
            df_estados = run_query(consultas['etas_estado'])
            
            if not df_estados.empty:
                fig = px.bar(df_estados.head(10), 
                           x='UF', y='Total ETAs', 
                           title="🏆 Top 10 Estados por Número de ETAs",
                           color='Total ETAs', 
                           color_continuous_scale='Blues',
                           text='Total ETAs')
                fig.update_traces(texttemplate='%{text}', textposition='outside')
                fig = create_styled_chart(fig, "🏆 Top 10 Estados por Número de ETAs")
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Erro: {e}")
    
    with col2:
        try:
            df_geo = run_query(consultas['analise_geografica'])
            
            if not df_geo.empty:
                regiao_totals = df_geo.groupby('Região')['Total Medições'].sum().reset_index()
                
                fig = px.pie(regiao_totals, 
                           values='Total Medições', 
                           names='Região',
                           title="🌍 Distribuição por Região",
                           color_discrete_sequence=px.colors.qualitative.Set3)
                fig = create_styled_chart(fig, "🌍 Distribuição por Região")
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Erro: {e}")
    
    # Resumo executivo
    st.markdown("### 📋 Resumo Executivo")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info("**Cobertura Nacional** - Sistema ativo em múltiplos estados com ampla distribuição geográfica")
    
    with col2:
        st.success("**Monitoramento Ativo** - Coleta contínua de dados de qualidade da água em tempo real")
    
    with col3:
        st.warning("**Diversidade Técnica** - Múltiplas tecnologias de tratamento em operação")

elif page == "🏭 Infraestrutura":
    st.markdown('<h2 class="section-header">Infraestrutura e Parâmetros</h2>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔧 Tecnologias de Tratamento", "🧪 Parâmetros de Qualidade"])
    
    with tab1:
        st.subheader("Tecnologias de Filtração")
        
        df_tech = run_query(consultas['etas_tecnologia'])
        
        if not df_tech.empty:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig = px.bar(df_tech, 
                           x='Tecnologia de Tratamento', y='Qtd ETAs',
                           title="Distribuição por Tecnologia",
                           color='Qtd ETAs', 
                           color_continuous_scale='viridis',
                           text='Qtd ETAs')
                fig.update_traces(texttemplate='%{text}', textposition='outside')
                fig.update_xaxes(tickangle=45)
                fig = create_styled_chart(fig, "Distribuição por Tecnologia")
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("### 📊 Resumo Estatístico")
                total_etas = df_tech['Qtd ETAs'].sum()
                for _, row in df_tech.iterrows():
                    st.metric(
                        label=row['Tecnologia de Tratamento'][:20] + "...",
                        value=f"{row['Qtd ETAs']:,}",
                        delta=f"{row['Percentual']:.1f}%"
                    )
                
                st.markdown(f"**Total de ETAs:** {total_etas:,}")
    
    with tab2:
        st.subheader("Parâmetros Monitorados")
        
        df_param = run_query(consultas['parametros_qualidade'])
        
        if not df_param.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                finalidade_count = df_param['Finalidade do Monitoramento'].value_counts()
                fig = px.pie(values=finalidade_count.values, 
                           names=finalidade_count.index,
                           title="Distribuição por Finalidade",
                           color_discrete_sequence=px.colors.qualitative.Pastel)
                fig = create_styled_chart(fig, "Distribuição por Finalidade")
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("### 🔍 Detalhamento por Categoria")
                for finalidade in df_param['Finalidade do Monitoramento'].unique():
                    params = df_param[df_param['Finalidade do Monitoramento'] == finalidade]
                    with st.expander(f"{finalidade} ({len(params)} parâmetros)"):
                        for _, param in params.iterrows():
                            unidade = param['Unidade'] if param['Unidade'] != 'None' else 'Qualitativo'
                            st.write(f"• **{param['Parâmetro de Qualidade']}** ({unidade})")

elif page == "🌍 Distribuição Territorial":
    st.markdown('<h2 class="section-header">Distribuição Territorial</h2>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["🗺️ Estados", "📍 Pontos de Coleta", "🧪 Parâmetros"])
    
    with tab1:
        st.subheader("Cobertura por Estado")
        
        df_estados = run_query(consultas['etas_estado'])
        
        if not df_estados.empty:
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            fig.add_trace(
                go.Bar(x=df_estados['UF'], 
                      y=df_estados['Total ETAs'], 
                      name="ETAs",
                      marker_color='steelblue'),
                secondary_y=False,
            )
            
            fig.add_trace(
                go.Scatter(x=df_estados['UF'], 
                          y=df_estados['Municípios com ETA'], 
                          mode='lines+markers', 
                          name="Municípios", 
                          line=dict(color='red', width=3),
                          marker=dict(size=8)),
                secondary_y=True,
            )
            
            fig.update_yaxes(title_text="Número de ETAs", secondary_y=False)
            fig.update_yaxes(title_text="Municípios Atendidos", secondary_y=True)
            fig = create_styled_chart(fig, "ETAs e Cobertura Municipal por Estado")
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabela com indicadores
            st.markdown("### 📊 Indicadores Detalhados")
            df_estados_display = df_estados.copy()
            df_estados_display['Eficiência'] = df_estados_display['ETAs por Município'].apply(lambda x: f"{x:.2f}")
            st.dataframe(df_estados_display, use_container_width=True)
    
    with tab2:
        st.subheader("Pontos de Monitoramento")
        
        df_pontos = run_query(consultas['medicoes_ponto'])
        
        if not df_pontos.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.pie(df_pontos, 
                           values='Total Medições', 
                           names='Ponto de Monitoramento',
                           title="Distribuição por Ponto")
                fig = create_styled_chart(fig, "Distribuição por Ponto")
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("### 📈 Análise Quantitativa")
                total_medicoes = df_pontos['Total Medições'].sum()
                for _, row in df_pontos.iterrows():
                    st.metric(
                        label=row['Ponto de Monitoramento'][:25] + "...",
                        value=f"{row['Total Medições']:,}",
                        delta=f"{row['% do Total']:.1f}%"
                    )
                st.markdown(f"**Total:** {total_medicoes:,} medições")
    
    with tab3:
        st.subheader("Categorias de Parâmetros")
        
        df_param_cat = run_query(consultas['parametros_categoria'])
        
        if not df_param_cat.empty:
            fig = px.sunburst(df_param_cat, 
                             path=['Categoria', 'Parâmetro'], 
                             values='Total Medições',
                             title="Hierarquia: Categorias → Parâmetros")
            fig = create_styled_chart(fig, "Hierarquia: Categorias → Parâmetros", 500)
            st.plotly_chart(fig, use_container_width=True)
            
            # Top parâmetros
            st.markdown("### 🔝 Top 10 Parâmetros Mais Monitorados")
            top_params = df_param_cat.nlargest(10, 'Total Medições')
            st.dataframe(top_params, use_container_width=True)

elif page == "🏢 Análise Institucional":
    st.markdown('<h2 class="section-header">Análise Institucional</h2>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["🌎 Panorama Regional", "🏛️ Performance Institucional", "⚙️ Eficácia por Tecnologia"])
    
    with tab1:
        st.subheader("Eficiência Regional")
        
        df_geo = run_query(consultas['analise_geografica'])
        
        if not df_geo.empty:
            fig = px.scatter(df_geo, 
                           x='ETAs Ativas', 
                           y='Total Medições', 
                           size='Medições/ETA', 
                           color='Região',
                           hover_name='UF',
                           title="Eficiência por Estado",
                           hover_data=['Municípios'])
            fig = create_styled_chart(fig, "Eficiência por Estado")
            st.plotly_chart(fig, use_container_width=True)
            
            # Resumo por região
            resumo_regiao = df_geo.groupby('Região').agg({
                'Total Medições': 'sum',
                'ETAs Ativas': 'sum',
                'Medições/ETA': 'mean',
                'Municípios': 'sum'
            }).round(1).reset_index()
            
            st.markdown("### 📋 Resumo Regional")
            st.dataframe(resumo_regiao, use_container_width=True)
    
    with tab2:
        st.subheader("Ranking Institucional")
        
        df_inst = run_query(consultas['performance_instituicao'])
        
        if not df_inst.empty:
            fig = px.scatter(df_inst, 
                           x='ETAs', 
                           y='Medições', 
                           size='Med/ETA',
                           color='Tipo',
                           hover_name='Instituição',
                           title="Performance: ETAs × Medições")
            fig = create_styled_chart(fig, "Performance: ETAs × Medições")
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("### 🏆 Ranking Detalhado")
            st.dataframe(df_inst, use_container_width=True)
    
    with tab3:
        st.subheader("Análise por Tecnologia de Filtração")
        
        df_filtrac = run_query(consultas['analise_filtracao'])
        
        if not df_filtrac.empty:
            # Análise por parâmetro
            parametros = df_filtrac['Parâmetro'].unique()
            
            for parametro in parametros:
                st.markdown(f"#### 📊 {parametro}")
                data_param = df_filtrac[df_filtrac['Parâmetro'] == parametro]
                
                if not data_param.empty:
                    fig = px.bar(data_param, 
                               x='Tipo Filtração', 
                               y='Porcentagem',
                               color='Faixa de Valores',
                               title=f"Distribuição de {parametro} por Tecnologia",
                               barmode='stack')
                    fig = create_styled_chart(fig, f"Distribuição de {parametro} por Tecnologia")
                    fig.update_xaxes(tickangle=45)
                    st.plotly_chart(fig, use_container_width=True)

elif page == "📈 Indicadores de Qualidade":
    st.markdown('<h2 class="section-header">Indicadores de Qualidade</h2>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🏆 Ranking de Estados", "🧪 Análise por Filtração"])
    
    with tab1:
        st.subheader("Ranking de Estados por Diversidade")
        
        df_ranking = run_query(consultas['ranking_estados'])
        
        if not df_ranking.empty:
            fig = px.bar(df_ranking.head(15), 
                        x='Estado', 
                        y='Parâmetros',
                        title="Top 15 Estados por Diversidade de Parâmetros",
                        color='Parâmetros', 
                        color_continuous_scale='RdYlGn',
                        text='Parâmetros')
            fig.update_traces(texttemplate='%{text}', textposition='outside')
            fig = create_styled_chart(fig, "Top 15 Estados por Diversidade de Parâmetros")
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
            
            if len(df_ranking) > 0:
                st.markdown("### 🎯 Principais Insights")
                
                col1, col2, col3 = st.columns(3)
                
                top_estado = df_ranking.iloc[0]
                with col1:
                    st.success(f"**Líder:** {top_estado['Estado']} com {int(top_estado['Parâmetros'])} parâmetros")
                
                avg_params = df_ranking['Parâmetros'].mean()
                with col2:
                    st.info(f"**Média nacional:** {avg_params:.0f} parâmetros/estado")
                
                total_medicoes = df_ranking['Medições'].sum()
                with col3:
                    st.warning(f"**Total analisado:** {total_medicoes:,} medições")
            
            st.markdown("### 📊 Tabela Completa")
            st.dataframe(df_ranking, use_container_width=True)
    
    with tab2:
        st.subheader("Análise Detalhada por Filtração")
        
        df_filtrac = run_query(consultas['analise_filtracao'])
        
        if not df_filtrac.empty:
            # Filtros interativos
            col1, col2 = st.columns(2)
            
            with col1:
                tecnologias = ['Todas'] + list(df_filtrac['Tipo Filtração'].unique())
                tech_selected = st.selectbox("Selecione a Tecnologia:", tecnologias)
            
            with col2:
                parametros = ['Todos'] + list(df_filtrac['Parâmetro'].unique())
                param_selected = st.selectbox("Selecione o Parâmetro:", parametros)
            
            # Filtrar dados
            df_filtered = df_filtrac.copy()
            if tech_selected != 'Todas':
                df_filtered = df_filtered[df_filtered['Tipo Filtração'] == tech_selected]
            if param_selected != 'Todos':
                df_filtered = df_filtered[df_filtered['Parâmetro'] == param_selected]
            
            if not df_filtered.empty:
                fig = px.scatter(df_filtered, 
                               x='Análises', 
                               y='Porcentagem',
                               size='ETAs',
                               color='Tipo Filtração',
                               hover_name='Faixa de Valores',
                               title="Análise de Performance por Tecnologia")
                fig = create_styled_chart(fig, "Análise de Performance por Tecnologia")
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(df_filtered, use_container_width=True)
            else:
                st.warning("Nenhum dado encontrado para os filtros selecionados.")

# NOVA PÁGINA: Evolução Temporal
elif page == "⏰ Evolução Temporal":
    st.markdown('<h2 class="section-header">Evolução Temporal do Monitoramento</h2>', unsafe_allow_html=True)
    
    df_temporal = run_query(consultas['evolucao_temporal'])
    
    if not df_temporal.empty:
        tab1, tab2, tab3 = st.tabs(["📈 Tendências Mensais", "🌍 Análise Regional", "📊 Métricas de Performance"])
        
        with tab1:
            st.subheader("Evolução Mensal por Região")
            
            # Gráfico de linha temporal
            fig = px.line(df_temporal, 
                         x='Mês', 
                         y='Total de Registros', 
                         color='Região',
                         title="Evolução dos Registros ao Longo do Ano",
                         markers=True)
            fig = create_styled_chart(fig, "Evolução dos Registros ao Longo do Ano")
            st.plotly_chart(fig, use_container_width=True)
            
            # Intensidade de monitoramento
            fig2 = px.line(df_temporal, 
                          x='Mês', 
                          y='Intensidade (Reg/ETA)', 
                          color='Região',
                          title="Intensidade de Monitoramento (Registros/ETA)",
                          markers=True)
            fig2 = create_styled_chart(fig2, "Intensidade de Monitoramento (Registros/ETA)")
            st.plotly_chart(fig2, use_container_width=True)
        
        with tab2:
            st.subheader("Comparação Regional")
            
            # Heatmap de intensidade
            pivot_intensidade = df_temporal.pivot(index='Região', columns='Mês', values='Intensidade (Reg/ETA)')
            
            fig = px.imshow(pivot_intensidade,
                           title="Mapa de Calor - Intensidade por Região e Mês",
                           color_continuous_scale='Viridis',
                           aspect='auto')
            fig = create_styled_chart(fig, "Mapa de Calor - Intensidade por Região e Mês", 400)
            st.plotly_chart(fig, use_container_width=True)
            
            # Análise por período
            periodo_summary = df_temporal.groupby(['Região', 'Período']).agg({
                'Total de Registros': 'sum',
                'Intensidade (Reg/ETA)': 'mean',
                'Diversidade (Par/ETA)': 'mean'
            }).round(2).reset_index()
            
            st.markdown("### 📋 Resumo por Período")
            st.dataframe(periodo_summary, use_container_width=True)
        
        with tab3:
            st.subheader("Métricas de Performance")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Diversidade de parâmetros
                fig = px.scatter(df_temporal, 
                               x='ETAs Ativas', 
                               y='Diversidade (Par/ETA)',
                               size='Total de Registros',
                               color='Região',
                               hover_data=['Mês'],
                               title="Diversidade vs ETAs Ativas")
                fig = create_styled_chart(fig, "Diversidade vs ETAs Ativas")
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Box plot da intensidade
                fig = px.box(df_temporal, 
                           x='Região', 
                           y='Intensidade (Reg/ETA)',
                           title="Distribuição da Intensidade por Região")
                fig = create_styled_chart(fig, "Distribuição da Intensidade por Região")
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
            
            # Métricas resumo
            st.markdown("### 🎯 Métricas Consolidadas")
            
            metricas_resumo = df_temporal.groupby('Região').agg({
                'Total de Registros': ['sum', 'mean'],
                'ETAs Ativas': 'mean',
                'Parâmetros Distintos': 'mean',
                'Intensidade (Reg/ETA)': ['mean', 'std'],
                'Diversidade (Par/ETA)': ['mean', 'std']
            }).round(2)
            
            # Achatando colunas multi-nível
            metricas_resumo.columns = ['_'.join(col).strip() for col in metricas_resumo.columns]
            st.dataframe(metricas_resumo, use_container_width=True)
    
    else:
        st.warning("⚠️ Dados temporais não disponíveis para análise.")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #64748b; padding: 20px;">
    <strong>SISAGUA - Sistema de Vigilância da Qualidade da Água</strong><br>
    Dashboard desenvolvido para análise do monitoramento nacional<br>
    <em>Fonte: SISAGUA 2025 | Última atualização: {}</em>
</div>
""".format(pd.Timestamp.now().strftime("%d/%m/%Y %H:%M")), unsafe_allow_html=True)