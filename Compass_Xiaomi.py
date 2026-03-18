import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import ta
import efinance as ef
from datetime import datetime, timedelta

# --- 页面配置 ---
st.set_page_config(page_title="多维量化投资罗盘 V13 完全体", layout="wide", page_icon="🧭")
st.title("🧭 核心资产多维量化系统 (V13 盘石计划完全体版)")

# 五大核心功能模块
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏆 AI 智能多维回测", 
    "📉 K线信号复盘", 
    "🕸️ 基本面估值雷达", 
    "🔥 组合相关性热力图",
    "🛡️ 组合压力测试 (盘石计划)"
])

# ==========================================
# 侧边栏：全局单股参数设置
# ==========================================
st.sidebar.header("⚙️ 全局单股分析设置")
ticker_dict = {
    "中国银行(金融护卫)": "601988",
    "中国海油(能源上游)": "600938",
    "小米集团-W(科技进攻)": "1810",
    "比亚迪(能源替代)": "002594",
    "中远海能(混乱溢价)": "600026",
    "紫金矿业(硬资产金)": "601899",
    "美的集团(稳健白马)": "000333",
    "中国移动(高息防守)": "600941",
    "商汤-W(AI弹性)": "00020",
    "药明生物(CXO)": "02269",
    "自定义输入...": "custom"
}
selected_name = st.sidebar.selectbox("选择分析标的", list(ticker_dict.keys()))
if selected_name == "自定义输入...":
    ticker = st.sidebar.text_input("请输入股票数字代码 (如 601988)", "601988")
else:
    ticker = ticker_dict[selected_name]

period = st.sidebar.selectbox("选择历史回测深度 (强烈建议5年以跨越牛熊)", ["1年", "2年", "3年", "5年"], index=3)

st.sidebar.markdown("---")
st.sidebar.info("💡 提示：【热力图】与【组合压力测试】为独立运算模块，可在对应标签页内直接点击运行。")
if st.sidebar.button("🚀 启动单股 AI 智能回测", type="primary", use_container_width=True):
    st.session_state.run_analysis = True

# ==========================================
# 核心引擎：数据抓取与指标计算
# ==========================================
@st.cache_data(ttl=3600) 
def load_and_calc_data(t, p):
    try:
        now = datetime.now()
        if p == "1年": days = 365
        elif p == "2年": days = 730
        elif p == "3年": days = 1095
        else: days = 1825
        beg = (now - timedelta(days=days)).strftime('%Y%m%d')
        
        df = ef.stock.get_quote_history(t, beg=beg)
        if df.empty: return pd.DataFrame()
        
        df.rename(columns={'日期': 'Date', '开盘': 'Open', '收盘': 'Close', '最高': 'High', '最低': 'Low', '成交量': 'Volume'}, inplace=True)
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        for col in ['Open', 'Close', 'High', 'Low', 'Volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(inplace=True)
        
        close_s = df['Close'].squeeze() 
        df['SMA_20'] = ta.trend.sma_indicator(close_s, window=20) 
        df['SMA_60'] = ta.trend.sma_indicator(close_s, window=60)
        df['RSI'] = ta.momentum.rsi(close_s, window=14)
        df['BB_High'] = ta.volatility.bollinger_hband(close_s, window=20, window_dev=2)
        df['BB_Low'] = ta.volatility.bollinger_lband(close_s, window=20, window_dev=2)
        df['MACD'] = ta.trend.macd(close_s)
        df['MACD_Signal'] = ta.trend.macd_signal(close_s)
        df['MACD_Hist'] = ta.trend.macd_diff(close_s)
        
        # 预判信号
        def get_left_signal(row):
            score = 0
            if row['RSI'] < 30: score += 1
            if row['Close'] < row['BB_Low']: score += 1
            if row['MACD_Hist'] > 0 and row['MACD'] < 0: score += 1
            if row['RSI'] > 70: score -= 1
            if row['Close'] > row['BB_High']: score -= 1
            if row['MACD_Hist'] < 0 and row['MACD'] > 0: score -= 1
            if score >= 2: return "买"
            elif score <= -2: return "卖"
            return "无"

        def get_right_signal(row):
            if row['Close'] > row['SMA_60'] and row['Close'] > row['SMA_20'] and row['MACD'] > row['MACD_Signal']: return "买"
            elif row['Close'] < row['SMA_20']: return "卖"
            return "无"

        df['Left_Sig'] = df.apply(get_left_signal, axis=1)
        df['Right_Sig'] = df.apply(get_right_signal, axis=1)
        
        return df
    except:
        return pd.DataFrame()

@st.cache_data(ttl=3600) 
def load_fundamentals(t):
    try:
        quote = ef.stock.get_latest_quote(t)
        if not quote.empty: return quote.iloc[0].to_dict()
    except: pass
    return {}

# 组合策略运算函数 (供 Tab 5 使用)
def run_strategy_sim(df, style, initial_cap=100000):
    cash, pos = initial_cap, 0
    equity = []
    for _, row in df.iterrows():
        price = row['Close']
        buy, sell = False, False
        
        if style == "左侧":
            if row['Left_Sig'] == "买": buy = True
            if row['Left_Sig'] == "卖": sell = True
        elif style == "右侧":
            if row['Right_Sig'] == "买": buy = True
            if row['Right_Sig'] == "卖": sell = True
        elif style == "死拿":
            buy = True # 第一天全仓买入
            
        if buy and pos == 0:
            pos = cash // price
            cash -= pos * price
        elif sell and pos > 0 and style != "死拿":
            cash += pos * price
            pos = 0
            
        equity.append(cash + pos * price)
    return equity

# ==========================================
# 单股分析主干逻辑 (Tab 1, 2, 3)
# ==========================================
if getattr(st.session_state, 'run_analysis', False):
    with st.spinner(f"正在全速运算 {ticker} 的基本面与全流派策略..."):
        df = load_and_calc_data(ticker, period)
        info = load_fundamentals(ticker)
        stock_name = info.get('名称', ticker)

    if not df.empty:
        initial_capital = 100000
        cash_l, pos_l = initial_capital, 0
        eq_l, log_l = [], []
        cash_r, pos_r = initial_capital, 0
        eq_r, log_r = [], []

        for date, row in df.iterrows():
            price = row['Close']
            # 左侧执行
            if row['Left_Sig'] == "买" and pos_l == 0:
                shares = cash_l // price
                cash_l -= shares * price
                pos_l = shares
                log_l.append('Buy')
            elif row['Left_Sig'] == "卖" and pos_l > 0:
                cash_l += pos_l * price
                pos_l = 0
                log_l.append('Sell')
            eq_l.append(cash_l + pos_l * price)
            
            # 右侧执行
            if row['Right_Sig'] == "买" and pos_r == 0:
                shares = cash_r // price
                cash_r -= shares * price
                pos_r = shares
                log_r.append('Buy')
            elif row['Right_Sig'] == "卖" and pos_r > 0:
                cash_r += pos_r * price
                pos_r = 0
                log_r.append('Sell')
            eq_r.append(cash_r + pos_r * price)

        df['Eq_Left'] = eq_l
        df['Eq_Right'] = eq_r
        df['Eq_Hold'] = initial_capital * (df['Close'] / df['Close'].iloc[0])

        ret_left = (df['Eq_Left'].iloc[-1] - initial_capital) / initial_capital * 100
        ret_right = (df['Eq_Right'].iloc[-1] - initial_capital) / initial_capital * 100
        ret_hold = (df['Eq_Hold'].iloc[-1] - initial_capital) / initial_capital * 100

        results = {"📉 左侧抄底波段": ret_left, "📈 右侧顺势追涨": ret_right, "🛡️ 无脑死拿一直抱": ret_hold}
        best_strategy = max(results, key=results.get)
        best_return = results[best_strategy]

        # --- TAB 1: AI 智能全自动回测 ---
        with tab1:
            st.markdown(f"""
            <div style="background-color: #1E1E1E; padding: 20px; border-radius: 10px; border: 2px solid {'#FFD700' if best_return > 0 else '#FF4500'};">
                <h2 style="text-align: center; color: white; margin-bottom: 0px;">🏆 AI 智能诊断结论</h2>
                <h4 style="text-align: center; color: #A0A0A0; margin-top: 10px;">经过过去 {period} 的数据极限推演，【{stock_name}】的真实股性最适合的交易流派是：</h4>
                <h1 style="text-align: center; color: {'#00FF7F' if best_return > 0 else '#FF6347'}; font-size: 3em; margin: 10px 0;">{best_strategy}</h1>
                <p style="text-align: center; color: white; font-size: 1.2em;">该流派历史总收益率可达：<strong>{best_return:.2f}%</strong></p>
            </div>
            <br>
            """, unsafe_allow_html=True)

            col_1, col_2, col_3 = st.columns(3)
            with col_1:
                st.info("### 🛡️ 流派一：一直死拿\n放弃择时，赚取分红与长期企业增长。适合低估值、高分红的成熟白马。")
                drawdown_h = ((df['Eq_Hold'] - df['Eq_Hold'].cummax()) / df['Eq_Hold'].cummax()).min() * 100
                st.metric("死拿总收益", f"{ret_hold:.2f}%", f"最大回撤 {drawdown_h:.2f}%", delta_color="inverse")
            with col_2:
                st.warning("### 📉 流派二：左侧抄底\n极限震荡高抛低吸。专治阴跌连连的熊市和宽幅震荡股。")
                drawdown_l = ((df['Eq_Left'] - df['Eq_Left'].cummax()) / df['Eq_Left'].cummax()).min() * 100
                st.metric("左侧总收益", f"{ret_left:.2f}%", f"最大回撤 {drawdown_l:.2f}% | 交易 {len([x for x in log_l if x == 'Sell'])} 次", delta_color="inverse")
            with col_3:
                st.success("### 📈 流派三：右侧追涨\n趋势跟踪，让利润奔跑。防范单边暴跌，适合科技医药股。")
                drawdown_r = ((df['Eq_Right'] - df['Eq_Right'].cummax()) / df['Eq_Right'].cummax()).min() * 100
                st.metric("右侧总收益", f"{ret_right:.2f}%", f"最大回撤 {drawdown_r:.2f}% | 交易 {len([x for x in log_r if x == 'Sell'])} 次", delta_color="inverse")

            st.divider()
            fig_all = go.Figure()
            fig_all.add_trace(go.Scatter(x=df.index, y=df['Eq_Hold'], mode='lines', name='无脑死拿资金线', line=dict(color='gray', width=1.5, dash='dash')))
            fig_all.add_trace(go.Scatter(x=df.index, y=df['Eq_Left'], mode='lines', name='左侧抄底资金线', line=dict(color='orange', width=2)))
            fig_all.add_trace(go.Scatter(x=df.index, y=df['Eq_Right'], mode='lines', name='右侧追涨资金线', line=dict(color='cyan', width=2)))
            fig_all.update_layout(title="💰 三大流派 资金曲线终极 PK 图", height=500, template="plotly_dark", hovermode="x unified")
            st.plotly_chart(fig_all, use_container_width=True)

        # --- TAB 2: K线信号复盘 ---
        with tab2:
            st.subheader(f"📉 {stock_name} ({ticker}) - 最佳策略信号复盘")
            if "右侧" in best_strategy:
                st.write("✨ 系统已自动为你展示【右侧】分析图表 (20日与60日均线体系)。")
                latest_sig = df.iloc[-1]['Right_Sig']
            elif "左侧" in best_strategy:
                st.write("✨ 系统已自动为你展示【左侧】分析图表 (布林带与RSI体系)。")
                latest_sig = df.iloc[-1]['Left_Sig']
            else:
                st.write("✨ 系统建议【死拿】，展示基础行情K线。")
                latest_sig = "无"
                
            col_s1, col_s2 = st.columns(2)
            col_s1.metric("最新收盘价", f"{df.iloc[-1]['Close']:.2f}")
            col_s2.metric("当前最新交易指令", "🟢 触发买入" if latest_sig == "买" else "🔴 触发止盈/止损" if latest_sig == "卖" else "⚪ 继续持有或观望")

            fig_k = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            fig_k.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K线'), row=1, col=1)
            if "右侧" in best_strategy or "死拿" in best_strategy:
                fig_k.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='cyan', width=2), name='20日生命线'), row=1, col=1)
                fig_k.add_trace(go.Scatter(x=df.index, y=df['SMA_60'], line=dict(color='orange', width=2), name='60日牛熊线'), row=1, col=1)
            if "左侧" in best_strategy:
                fig_k.add_trace(go.Scatter(x=df.index, y=df['BB_High'], line=dict(color='rgba(255,0,0,0.5)', width=1, dash='dot'), name='布林带上轨'), row=1, col=1)
                fig_k.add_trace(go.Scatter(x=df.index, y=df['BB_Low'], line=dict(color='rgba(0,255,0,0.5)', width=1, dash='dot'), name='布林带下轨'), row=1, col=1)

            colors = ['red' if row['Open'] > row['Close'] else 'green' for index, row in df.iterrows()]
            fig_k.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='成交量'), row=2, col=1)
            fig_k.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
            fig_k.update_layout(height=600, xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_k, use_container_width=True)

        # --- TAB 3: 基本面估值雷达 ---
        with tab3:
            st.subheader(f"🛡️ {stock_name} - 基本面六边形体检报告")
            def parse_float(val, default=0):
                if val == '-' or pd.isna(val) or val == 'N/A': return default
                try: return float(val)
                except: return default

            pe = parse_float(info.get('动态市盈率', '-'))
            pb = parse_float(info.get('市净率', '-'))
            market_cap = parse_float(info.get('总市值', '0')) / 1e8 
            turnover = parse_float(info.get('换手率', '0'))
            rsi_val = df.iloc[-1]['RSI']
            
            pe_score = 10 if pe <= 0 else 90 if pe < 15 else 60 if pe < 30 else max(10, 100 - (pe - 30))
            pb_score = 10 if pb <= 0 else 90 if pb < 2 else 60 if pb < 5 else max(10, 100 - (pb * 10))
            size_score = min(100, (market_cap / 1000) * 100) if market_cap > 0 else 10
            liq_score = min(100, turnover * 10) if turnover > 0 else 10
            mom_score = 100 - abs(rsi_val - 50) * 2

            categories = ['估值安全度 (低PE)', '资产性价比 (低PB)', '规模护城河 (大市值)', '市场流动性 (高换手)', '量化动能 (RSI健康度)']
            scores = [pe_score, pb_score, size_score, liq_score, mom_score]
            
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=scores + [scores[0]], theta=categories + [categories[0]], fill='toself',
                fillcolor='rgba(50, 205, 50, 0.4)' if np.mean(scores) > 50 else 'rgba(255, 69, 0, 0.4)',
                line=dict(color='limegreen' if np.mean(scores) > 50 else 'orangered', width=2), name=stock_name
            ))
            fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False, height=500, template="plotly_dark")
            
            col_rad1, col_rad2 = st.columns([1, 1])
            with col_rad1: st.plotly_chart(fig_radar, use_container_width=True)
            with col_rad2:
                st.markdown("### 📋 诊断简报")
                st.markdown(f"- **总市值:** {market_cap:.2f} 亿元")
                st.markdown(f"- **动态市盈率 (PE):** {pe if pe > 0 else '亏损或不可用'}")
                st.markdown(f"- **市净率 (PB):** {pb}")
                st.markdown("---")
                if pe_score >= 80 and size_score >= 80: st.success("💎 **护城河极深，估值合理**。典型的价值白马股，底气十足。")
                elif pe <= 0: st.error("⚠️ **公司目前处于亏损状态**。雷达图安全度塌陷，只能依赖技术面炒预期，绝不能死扛！")
                else: st.info("⚖️ **基本面中规中矩**。需重点结合 Tab 1 的 AI 策略胜率来决定买卖流派。")
    else:
        st.error("无法获取数据，请检查网络或股票代码。")

else:
    with tab1: st.info("👈 请在左侧选择标的并点击启动回测。")
    with tab2: st.info("👈 待回测启动后生成图表。")
    with tab3: st.info("👈 待回测启动后生成雷达图。")

# ==========================================
# TAB 4: 组合相关性热力图 (独立运算)
# ==========================================
with tab4:
    st.markdown("### 🔍 投资组合防暴雷检测系统 (独立运算)")
    all_stocks_pool = {
        "中国银行(金融)": "601988", "中国海油(能源)": "600938", "小米(科技)": "1810", 
        "比亚迪(电车)": "002594", "中远海能(航运)": "600026", "紫金矿业(黄金)": "601899",
        "美的(家电)": "000333", "商汤(AI)": "00020", "药明(CXO)": "02269"
    }
    selected_assets = st.multiselect("📝 选择检测资产（盘石计划默认）", options=list(all_stocks_pool.keys()), 
                                     default=["中国银行(金融)", "中国海油(能源)", "小米(科技)", "比亚迪(电车)", "中远海能(航运)", "紫金矿业(黄金)"])
    corr_period = st.selectbox("📅 统计周期", ["近半年", "近1年", "近2年", "近5年"], index=3)

    if st.button("🔥 生成相关性矩阵", type="primary"):
        if len(selected_assets) < 2:
            st.warning("至少需要选择两只以上的资产。")
        else:
            with st.spinner("正在并发抓取收盘价并计算矩阵..."):
                now = datetime.now()
                days = 1825 if corr_period == "近5年" else 730 if corr_period == "近2年" else 365 if corr_period == "近1年" else 180
                beg = (now - timedelta(days=days)).strftime('%Y%m%d')

                price_dict = {}
                for name in selected_assets:
                    try:
                        df_s = ef.stock.get_quote_history(all_stocks_pool[name], beg=beg)
                        if not df_s.empty:
                            df_s['日期'] = pd.to_datetime(df_s['日期'])
                            df_s.set_index('日期', inplace=True)
                            price_dict[name] = pd.to_numeric(df_s['收盘'], errors='coerce')
                    except: pass

                if price_dict:
                    portfolio_df = pd.DataFrame(price_dict).dropna()
                    corr_matrix = portfolio_df.corr()
                    fig_corr = px.imshow(corr_matrix, text_auto=".2f", aspect="auto", color_continuous_scale="RdBu_r", zmin=-1, zmax=1)
                    fig_corr.update_layout(height=600, template="plotly_dark", margin=dict(l=20, r=20, t=30, b=20))
                    st.plotly_chart(fig_corr, use_container_width=True)

# ==========================================
# TAB 5: 组合压力测试 (盘石计划 核心推演)
# ==========================================
with tab5:
    st.subheader("🏗️ “盘石计划”组合兵棋推演 (5年极限压力测试)")
    st.markdown("通过量化历史回测，检验**金融+能源+科技+硬资产**的 4-4-2 结构能否抵御系统性风险。")
    
    panshi_pool = {
        "中国银行 (防御死拿)": "601988",
        "中国海油 (通胀死拿)": "600938",
        "小米集团 (科技追涨)": "1810",
        "比亚迪 (制造追涨)": "002594",
        "中远海能 (航运追涨)": "600026",
        "紫金矿业 (避险死拿)": "601899"
    }
    
    st.markdown("#### 1. 分配初始资金权重 (%)")
    cols = st.columns(3)
    weights = {}
    default_w = [20, 20, 20, 20, 10, 10] # 4-4-2 比例
    
    for i, (name, code) in enumerate(panshi_pool.items()):
        with cols[i % 3]:
            weights[name] = st.slider(f"{name}", 0, 100, default_w[i])
    
    total_w = sum(weights.values())
    st.write(f"**当前总权重：{total_w}%**")
    
    if total_w != 100:
        st.error("❌ 请调整滑块，使总权重严格等于 100% 才能启动模拟。")
    else:
        if st.button("🔥 开始全组合压力测试", type="primary", use_container_width=True):
            with st.spinner("正在并发拉取 6 大护国重器数据，并合成航母编队资金曲线..."):
                days_test = 1825 # 强制 5 年回测
                portfolio_results = []
                
                for name, weight in weights.items():
                    code = panshi_pool[name]
                    df_stock = load_and_calc_data(code, "5年")
                    
                    if not df_stock.empty:
                        # 核心：给不同资产分配最强基因策略
                        strategy = "右侧" if "追涨" in name else "死拿"
                        eq = run_strategy_sim(df_stock, strategy)
                        # 将金额转换为归一化收益贡献
                        weighted_eq = (np.array(eq) / 100000) * (weight / 100)
                        portfolio_results.append(weighted_eq)
                
                if portfolio_results:
                    # 对齐时间轴最小长度
                    min_len = min([len(r) for r in portfolio_results])
                    final_portfolio_eq = np.zeros(min_len)
                    for r in portfolio_results:
                        final_portfolio_eq += r[:min_len]
                    
                    port_return = (final_portfolio_eq[-1] - 1) * 100
                    roll_max = pd.Series(final_portfolio_eq).cummax()
                    port_max_dd = ((final_portfolio_eq - roll_max) / roll_max).min() * 100
                    
                    st.divider()
                    c1, c2, c3 = st.columns(3)
                    c1.metric("组合预期总收益 (5年)", f"{port_return:.2f}%")
                    c2.metric("组合极端最大回撤", f"{port_max_dd:.2f}%", delta_color="inverse")
                    c3.metric("风险收益比 (Calmar)", f"{abs(port_return/port_max_dd):.2f}" if port_max_dd != 0 else "N/A")
                    
                    fig_port = go.Figure()
                    fig_port.add_trace(go.Scatter(y=final_portfolio_eq, mode='lines', name='盘石计划 整体净值', line=dict(color='limegreen', width=3)))
                    fig_port.update_layout(
                        title="📈 “盘石计划” 组合模拟净值曲线 (近5年实战推演)",
                        xaxis_title="交易天数 (滑动查看历史事件节点)",
                        yaxis_title="账户净值 (初始为 1.0)",
                        template="plotly_dark",
                        height=500,
                        hovermode="x unified"
                    )
                    st.plotly_chart(fig_port, use_container_width=True)
                    
                    st.success("📝 **AI 阵型诊断：** 在这个防御组合中，系统已自动为您的金融、能源和黄金底座开启了【死拿】收息模式；同时为科技、智造和航运开启了【右侧趋势】防守模式。请观察资金曲线在 2022 年或 2024 年极端行情中的平滑程度！")