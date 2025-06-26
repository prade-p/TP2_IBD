import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3

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

# Consultas SQL
def get_consultas():
    return {
        'etas_tecnologia': '''
        SELECT 
            nome_eta as "Nome da ETA",
            tipo_filtracao as "Tecnologia de Tratamento"
        FROM ETA 
        WHERE tipo_filtracao IS NOT NULL AND tipo_filtracao != ''
        ORDER BY tipo_filtracao, nome_eta
        ''',
        
        'parametros_qualidade': '''
        SELECT 
            nome_parametro as "Parâmetro",
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
            END as "Finalidade"
        FROM Parametro 
        WHERE nome_parametro IS NOT NULL AND nome_parametro != ''
        ORDER BY nome_parametro
        ''',
        
        'etas_estado': '''
        SELECT 
            e.nome_estado as "Estado",
            COUNT(DISTINCT eta.id_eta) as "Total de ETAs",
            COUNT(DISTINCT mun.id_municipio) as "Municípios Atendidos"
        FROM Estado e
        INNER JOIN Municipio mun ON e.id_estado = mun.id_estado
        INNER JOIN ETA eta ON mun.id_municipio = eta.id_municipio
        GROUP BY e.nome_estado
        HAVING COUNT(DISTINCT eta.id_eta) > 0
        ORDER BY COUNT(DISTINCT eta.id_eta) DESC
        LIMIT 15
        ''',
        
        'medicoes_ponto': '''
        SELECT 
            pm.nome_ponto as "Ponto de Monitoramento",
            COUNT(m.id_medicao) as "Total de Medições",
            ROUND(COUNT(m.id_medicao) * 100.0 / (SELECT COUNT(*) FROM Medicao), 1) as "Percentual"
        FROM Ponto_Monitoramento pm
        INNER JOIN Medicao m ON pm.id_ponto = m.id_ponto
        GROUP BY pm.nome_ponto
        ORDER BY COUNT(m.id_medicao) DESC
        ''',
        
        'parametros_categoria': '''
        SELECT 
            p.categoria_parametro as "Categoria",
            p.nome_parametro as "Parâmetro",
            COUNT(m.id_medicao) as "Total de Medições"
        FROM Parametro p
        INNER JOIN Medicao m ON p.id_parametro = m.id_parametro
        GROUP BY p.categoria_parametro, p.nome_parametro
        ORDER BY COUNT(m.id_medicao) DESC
        ''',
        
        'analise_geografica': '''
        SELECT 
            r.nome_regiao as "Região",
            e.nome_estado as "Estado",
            COUNT(DISTINCT mun.id_municipio) as "Municípios",
            COUNT(DISTINCT eta.id_eta) as "ETAs Ativas",
            COUNT(med.id_medicao) as "Total de Medições",
            ROUND(COUNT(med.id_medicao) * 1.0 / COUNT(DISTINCT eta.id_eta), 0) as "Eficiência"
        FROM Regiao r
        INNER JOIN Estado e ON r.id_regiao = e.id_regiao
        INNER JOIN Municipio mun ON e.id_estado = mun.id_estado
        INNER JOIN ETA eta ON mun.id_municipio = eta.id_municipio
        INNER JOIN Medicao med ON eta.id_eta = med.id_eta
        GROUP BY r.nome_regiao, e.nome_estado
        HAVING COUNT(med.id_medicao) > 0
        ORDER BY COUNT(med.id_medicao) DESC
        LIMIT 20
        ''',
        
        'performance_instituicao': '''
        SELECT 
            i.nome_instituicao as "Instituição",
            COUNT(DISTINCT eta.id_eta) as "ETAs",
            COUNT(med.id_medicao) as "Medições",
            ROUND(COUNT(med.id_medicao) * 1.0 / COUNT(DISTINCT eta.id_eta), 0) as "Produtividade"
        FROM Instituicao i
        INNER JOIN Escritorio_Regional er ON i.id_instituicao = er.id_instituicao
        INNER JOIN ETA eta ON er.id_escritorio = eta.id_escritorio
        INNER JOIN Medicao med ON eta.id_eta = med.id_eta
        GROUP BY i.nome_instituicao
        HAVING COUNT(med.id_medicao) > 1000
        ORDER BY COUNT(med.id_medicao) DESC
        LIMIT 8
        ''',
        
        'analise_filtracao': '''
        SELECT 
            eta.tipo_filtracao as "Tipo de Filtração",
            p.nome_parametro as "Parâmetro",
            COUNT(med.id_medicao) as "Análises",
            ROUND(AVG(CASE WHEN med.valor_medido > 0 THEN med.valor_medido END), 2) as "Valor Médio"
        FROM ETA eta
        INNER JOIN Medicao med ON eta.id_eta = med.id_eta
        INNER JOIN Parametro p ON med.id_parametro = p.id_parametro
        INNER JOIN Campo c ON med.id_campo = c.id_campo
        WHERE p.nome_parametro IN ('Turbidez (uT)', 'Cloro Residual Livre (mg/L)', 'pH')
          AND c.categoria_campo = 'Estatísticas'
          AND eta.tipo_filtracao IS NOT NULL
        GROUP BY eta.tipo_filtracao, p.nome_parametro
        HAVING COUNT(med.id_medicao) >= 10
        ORDER BY eta.tipo_filtracao, COUNT(med.id_medicao) DESC
        ''',
        
        'estatisticas_regiao': '''
        SELECT 
            r.nome_regiao as "Região",
            p.nome_parametro as "Parâmetro",
            COUNT(med.id_medicao) as "Medições",
            ROUND(AVG(med.valor_medido), 2) as "Valor Médio",
            ROUND(MIN(med.valor_medido), 2) as "Mínimo",
            ROUND(MAX(med.valor_medido), 2) as "Máximo"
        FROM Regiao r
        INNER JOIN Estado e ON r.id_regiao = e.id_regiao
        INNER JOIN Municipio mun ON e.id_estado = mun.id_estado
        INNER JOIN ETA eta ON mun.id_municipio = eta.id_municipio
        INNER JOIN Medicao med ON eta.id_eta = med.id_eta
        INNER JOIN Parametro p ON med.id_parametro = p.id_parametro
        WHERE med.valor_medido IS NOT NULL 
          AND med.valor_medido > 0
          AND p.nome_parametro IN ('Turbidez (uT)', 'Cloro Residual Livre (mg/L)', 'pH')
        GROUP BY r.nome_regiao, p.nome_parametro
        HAVING COUNT(med.id_medicao) >= 100
        ORDER BY r.nome_regiao, COUNT(med.id_medicao) DESC
        ''',
        
        'ranking_estados': '''
        SELECT 
            e.nome_estado as "Estado",
            COUNT(DISTINCT eta.id_eta) as "ETAs",
            COUNT(med.id_medicao) as "Medições",
            ROUND(COUNT(med.id_medicao) * 1.0 / COUNT(DISTINCT eta.id_eta), 0) as "Eficiência"
        FROM Estado e
        INNER JOIN Municipio mun ON e.id_estado = mun.id_estado
        INNER JOIN ETA eta ON mun.id_municipio = eta.id_municipio
        INNER JOIN Medicao med ON eta.id_eta = med.id_eta
        GROUP BY e.nome_estado
        HAVING COUNT(DISTINCT eta.id_eta) >= 5
        ORDER BY COUNT(med.id_medicao) * 1.0 / COUNT(DISTINCT eta.id_eta) DESC
        LIMIT 12
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
        '''
    }

# Header principal
st.markdown('<h1 class="main-header">💧 SISAGUA - Monitoramento da Qualidade da Água</h1>', unsafe_allow_html=True)

# Sidebar
st.sidebar.title("Navegação")
page = st.sidebar.selectbox(
    "Escolha uma seção:",
    [
        "Visão Geral",
        "Infraestrutura", 
        "Distribuição Territorial",
        "Análise Institucional", 
        "Indicadores de Qualidade"
    ]
)

consultas = get_consultas()

# Páginas
if page == "Visão Geral":
    st.markdown('<h2 class="section-header">Panorama do Sistema SISAGUA</h2>', unsafe_allow_html=True)
    
    # Métricas principais
    try:
        df_metricas = run_query(consultas['metricas_gerais'])
        
        col1, col2, col3, col4 = st.columns(4)
        
        for i, (_, row) in enumerate(df_metricas.iterrows()):
            cols = [col1, col2, col3, col4]
            with cols[i]:
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
                           x='Estado', y='Total de ETAs', 
                           title="🏆 Top 10 Estados por Número de ETAs",
                           color='Total de ETAs', 
                           color_continuous_scale='Blues')
                fig.update_layout(showlegend=False, height=450)
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Erro: {e}")
    
    with col2:
        try:
            df_geo = run_query(consultas['analise_geografica'])
            
            if not df_geo.empty:
                regiao_totals = df_geo.groupby('Região')['Total de Medições'].sum().reset_index()
                
                fig = px.pie(regiao_totals, 
                           values='Total de Medições', 
                           names='Região',
                           title="🌍 Distribuição por Região",
                           color_discrete_sequence=px.colors.qualitative.Set3)
                fig.update_layout(height=450)
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Erro: {e}")

elif page == "Infraestrutura":
    st.markdown('<h2 class="section-header">Infraestrutura e Parâmetros</h2>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Tecnologias de Tratamento", "Parâmetros de Qualidade"])
    
    with tab1:
        st.subheader("Tecnologias de Filtração")
        
        df_tech = run_query(consultas['etas_tecnologia'])
        
        if not df_tech.empty:
            tech_count = df_tech['Tecnologia de Tratamento'].value_counts().reset_index()
            tech_count.columns = ['Tecnologia', 'Quantidade']
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig = px.bar(tech_count, 
                           x='Tecnologia', y='Quantidade',
                           title="Distribuição por Tecnologia",
                           color='Quantidade', 
                           color_continuous_scale='viridis')
                fig.update_xaxes(tickangle=45)
                fig.update_layout(height=450)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("### Resumo")
                for _, row in tech_count.iterrows():
                    percentage = (row['Quantidade'] / tech_count['Quantidade'].sum()) * 100
                    st.metric(
                        label=row['Tecnologia'],
                        value=f"{row['Quantidade']:,}",
                        delta=f"{percentage:.1f}%"
                    )
    
    with tab2:
        st.subheader("Parâmetros Monitorados")
        
        df_param = run_query(consultas['parametros_qualidade'])
        
        if not df_param.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                finalidade_count = df_param['Finalidade'].value_counts()
                fig = px.pie(values=finalidade_count.values, 
                           names=finalidade_count.index,
                           title="Distribuição por Finalidade",
                           color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("### Detalhamento")
                for finalidade in df_param['Finalidade'].unique():
                    params = df_param[df_param['Finalidade'] == finalidade]
                    with st.expander(f"{finalidade} ({len(params)})"):
                        for _, param in params.iterrows():
                            unidade = param['Unidade'] if param['Unidade'] != 'None' else 'Qualitativo'
                            st.write(f"• {param['Parâmetro']} ({unidade})")

elif page == "Distribuição Territorial":
    st.markdown('<h2 class="section-header">Distribuição Territorial</h2>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Estados", "Pontos de Coleta", "Parâmetros"])
    
    with tab1:
        st.subheader("Cobertura por Estado")
        
        df_estados = run_query(consultas['etas_estado'])
        
        if not df_estados.empty:
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            fig.add_trace(
                go.Bar(x=df_estados['Estado'], 
                      y=df_estados['Total de ETAs'], 
                      name="ETAs",
                      marker_color='steelblue'),
                secondary_y=False,
            )
            
            fig.add_trace(
                go.Scatter(x=df_estados['Estado'], 
                          y=df_estados['Municípios Atendidos'], 
                          mode='lines+markers', 
                          name="Municípios", 
                          line=dict(color='red', width=3)),
                secondary_y=True,
            )
            
            fig.update_yaxes(title_text="Número de ETAs", secondary_y=False)
            fig.update_yaxes(title_text="Municípios", secondary_y=True)
            fig.update_layout(title_text="ETAs e Cobertura Municipal", height=450)
            fig.update_xaxes(tickangle=45)
            
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df_estados, use_container_width=True)
    
    with tab2:
        st.subheader("Pontos de Monitoramento")
        
        df_pontos = run_query(consultas['medicoes_ponto'])
        
        if not df_pontos.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.pie(df_pontos, 
                           values='Total de Medições', 
                           names='Ponto de Monitoramento',
                           title="Distribuição por Ponto")
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("### Análise")
                for _, row in df_pontos.iterrows():
                    st.metric(
                        label=row['Ponto de Monitoramento'],
                        value=f"{row['Total de Medições']:,}",
                        delta=f"{row['Percentual']}%"
                    )
    
    with tab3:
        st.subheader("Categorias de Parâmetros")
        
        df_param_cat = run_query(consultas['parametros_categoria'])
        
        if not df_param_cat.empty:
            fig = px.sunburst(df_param_cat, 
                             path=['Categoria', 'Parâmetro'], 
                             values='Total de Medições',
                             title="Hierarquia: Categorias → Parâmetros")
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)

elif page == "Análise Institucional":
    st.markdown('<h2 class="section-header">Análise Institucional</h2>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Panorama Regional", "Performance Institucional", "Eficácia por Tecnologia"])
    
    with tab1:
        st.subheader("Eficiência Regional")
        
        df_geo = run_query(consultas['analise_geografica'])
        
        if not df_geo.empty:
            fig = px.scatter(df_geo, 
                           x='ETAs Ativas', 
                           y='Total de Medições', 
                           size='Eficiência', 
                           color='Região',
                           hover_name='Estado',
                           title="Eficiência por Estado")
            fig.update_layout(height=450)
            st.plotly_chart(fig, use_container_width=True)
            
            resumo_regiao = df_geo.groupby('Região').agg({
                'Total de Medições': 'sum',
                'ETAs Ativas': 'sum',
                'Eficiência': 'mean'
            }).round(1).reset_index()
            
            st.dataframe(resumo_regiao, use_container_width=True)
    
    with tab2:
        st.subheader("Ranking Institucional")
        
        df_inst = run_query(consultas['performance_instituicao'])
        
        if not df_inst.empty:
            fig = px.scatter(df_inst, 
                           x='ETAs', 
                           y='Medições', 
                           size='Produtividade',
                           hover_name='Instituição',
                           title="Performance: ETAs × Medições")
            fig.update_layout(height=450)
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(df_inst, use_container_width=True)
    
    with tab3:
        st.subheader("Análise por Tecnologia")
        
        df_filtrac = run_query(consultas['analise_filtracao'])
        
        if not df_filtrac.empty:
            turbidez_data = df_filtrac[df_filtrac['Parâmetro'] == 'Turbidez (uT)']
            cloro_data = df_filtrac[df_filtrac['Parâmetro'] == 'Cloro Residual Livre (mg/L)']
            
            col1, col2 = st.columns(2)
            
            if not turbidez_data.empty:
                with col1:
                    fig = px.bar(turbidez_data, 
                               x='Tipo de Filtração', 
                               y='Valor Médio',
                               title="Turbidez por Tecnologia")
                    fig.update_xaxes(tickangle=45)
                    st.plotly_chart(fig, use_container_width=True)
            
            if not cloro_data.empty:
                with col2:
                    fig = px.bar(cloro_data, 
                               x='Tipo de Filtração', 
                               y='Valor Médio',
                               title="Cloro por Tecnologia")
                    fig.update_xaxes(tickangle=45)
                    st.plotly_chart(fig, use_container_width=True)

elif page == "Indicadores de Qualidade":
    st.markdown('<h2 class="section-header">Indicadores de Qualidade</h2>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📊 Estatísticas por Região", "Ranking de Eficiência"])
    
    with tab1:
        st.subheader("Estatísticas Regionais")
        
        df_stats = run_query(consultas['estatisticas_regiao'])
        
        if not df_stats.empty:
            fig = px.bar(df_stats, 
                       x='Região', 
                       y='Valor Médio', 
                       color='Parâmetro',
                       title="Valores Médios por Região",
                       barmode='group')
            fig.update_layout(height=450)
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(df_stats, use_container_width=True)
    
    with tab2:
        st.subheader("Ranking de Estados")
        
        df_ranking = run_query(consultas['ranking_estados'])
        
        if not df_ranking.empty:
            fig = px.bar(df_ranking, 
                        x='Estado', 
                        y='Eficiência',
                        title="Eficiência por Estado",
                        color='Eficiência', 
                        color_continuous_scale='RdYlGn')
            fig.update_layout(height=450)
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
            
            if len(df_ranking) > 0:
                st.markdown("### Principais Insights")
                
                col1, col2, col3 = st.columns(3)
                
                top_estado = df_ranking.iloc[0]
                with col1:
                    st.success(f"Líder: {top_estado['Estado']} com {int(top_estado['Eficiência'])} medições/ETA")
                
                avg_efficiency = df_ranking['Eficiência'].mean()
                with col2:
                    st.info(f"Eficiência média: {avg_efficiency:.0f} medições/ETA")
                
                total_medicoes = df_ranking['Medições'].sum()
                with col3:
                    st.warning(f"Total: {total_medicoes:,} medições analisadas")
            
            st.dataframe(df_ranking, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #64748b; padding: 20px;">
    <strong>SISAGUA - Sistema de Vigilância da Qualidade da Água</strong><br>
    Dashboard desenvolvido para análise do monitoramento nacional<br>
    <em>Fonte: SISAGUA 2025</em>
</div>
""", unsafe_allow_html=True)