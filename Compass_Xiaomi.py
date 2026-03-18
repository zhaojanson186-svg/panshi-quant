import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import ta
import yfinance as yf
from datetime import datetime, timedelta

# --- 页面配置 ---
st.set_page_config(page_title="多维量化投资罗盘 V13 云端版", layout="wide", page_icon="🧭")
st.title("🧭 核心资产多维量化系统 (V13 盘石计划·云端版)")

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
    ticker = st.sidebar.text_input("请输入股票代码 (如 601988)", "601988")
else:
    ticker = ticker_dict[selected_name]

period = st.sidebar.selectbox("选择历史回测深度", ["1年", "2年", "3年", "5年"], index=3)

st.sidebar.markdown("---")
st.sidebar.info("💡 提示：云端版已接入雅虎财经全球行情专线。")
if st.sidebar.button("🚀 启动单股 AI 智能回测", type="primary", use_container_width=True):
    st.session_state.run_analysis = True

# ==========================================
# 核心引擎：雅虎财经数据抓取与计算
# ==========================================
def get_yf_ticker(code):
    # 智能转换 A股和港股代码后缀
    if code.startswith('6'): return f"{code}.SS"
    elif code.startswith('0') or code.startswith('3'):
        if len(code) == 6: return f"{code}.SZ"
    elif len(code) <= 5: 
        return f"{int(code):04d}.HK"
    return code

@st.cache_data(ttl=3600) 
def load_and_calc_data(t, p):
    try:
        yf_ticker = get_yf_ticker(t)
        p_map = {"1年": "1y", "2年": "2y", "3年": "3y", "5年": "5y"}
        df = yf.Ticker(yf_ticker).history(period=p_map.get(p, "5y"))
        
        if df.empty: return pd.DataFrame()
        
        df.reset_index(inplace=True)
        date_col = 'Date' if 'Date' in df.columns else 'Datetime'
        df.rename(columns={date_col: 'Date'}, inplace=True)
        df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
        df.set_index('Date', inplace=True)
        
        close_s = df['Close'].squeeze() 
        df['SMA_20'] = ta.trend.sma_indicator(close_s, window=20) 
        df['SMA_60'] = ta.trend.sma_indicator(close_s, window=60)
        df['RSI'] = ta.momentum.rsi(close_s, window=14)
        df['BB_High'] = ta.volatility.bollinger_hband(close_s, window=20, window_dev=2)
        df['BB_Low'] = ta.volatility.bollinger_lband(close_s, window=20, window_dev=2)
        df['MACD'] = ta.trend.macd(close_s)
        df['MACD_Signal'] = ta.trend.macd_signal(close_s)
        df['MACD_Hist'] = ta.trend.macd_diff(close_s)
        
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
        yf_ticker = get_yf_ticker(t)
        info = yf.Ticker(yf_ticker).info
        market_cap = info.get('marketCap', 0)
        return {
            '名称': info.get('shortName', t),
            '动态市盈率': info.get('trailingPE', '-'),
            '市净率': info.get('priceToBook', '-'),
            '总市值': market_cap,
            '换手率': info.get('volume', 0) / info.get('sharesOutstanding', 1) if info.get('sharesOutstanding') else 0
        }
    except:
        return {}

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
            buy = True 
            
        if buy and pos == 0:
            pos = cash // price
            cash -= pos * price
        elif sell and pos > 0 and style != "死拿":
            cash += pos * price
            pos = 0
        equity.append(cash + pos * price)
    return equity

# ==========================================
# 单股分析主干逻辑 
# ==========================================
if getattr(st.session_state, 'run_analysis', False):
    with st.spinner(f"正在通过雅虎财经专线抓取 {ticker} 数据..."):
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

        with tab1:
            st.markdown(f"""
            <div style="background-color: #1E1E1E; padding: 20px; border-radius: 10px; border: 2px solid {'#FFD700' if best_return > 0 else '#FF4500'};">
                <h2 style="text-align: center; color: white; margin-bottom: 0px;">🏆 AI 智能诊断结论</h2>
                <h4 style="text-align: center; color: #A0A0A0; margin-top: 10px;">经过过去 {period} 的数据极限推演，【{stock_name}】最适合的流派是：</h4>
                <h1 style="text-align: center; color: {'#00FF7F' if best_return > 0 else '#FF6347'}; font-size: 3em; margin: 10px 0;">{best_strategy}</h1>
                <p style="text-align: center; color: white; font-size: 1.2em;">历史总收益率可达：<strong>{best_return:.2f}%</strong></p>
            </div>
            <br>
            """, unsafe_allow_html=True)
            col_1, col_2, col_3 = st.columns(3)
            with col_1:
                drawdown_h = ((df['Eq_Hold'] - df['Eq_Hold'].cummax()) / df['Eq_Hold'].cummax()).min() * 100
                st.metric("死拿总收益", f"{ret_hold:.2f}%", f"最大回撤 {drawdown_h:.2f}%", delta_color="inverse")
            with col_2:
                drawdown_l = ((df['Eq_Left'] - df['Eq_Left'].cummax()) / df['Eq_Left'].cummax()).min() * 100
                st.metric("左侧总收益", f"{ret_left:.2f}%", f"最大回撤 {drawdown_l:.2f}%", delta_color="inverse")
            with col_3:
                drawdown_r = ((df['Eq_Right'] - df['Eq_Right'].cummax()) / df['Eq_Right'].cummax()).min() * 100
                st.metric("右侧总收益", f"{ret_right:.2f}%", f"最大回撤 {drawdown_r:.2f}%", delta_color="inverse")

            fig_all = go.Figure()
            fig_all.add_trace(go.Scatter(x=df.index, y=df['Eq_Hold'], mode='lines', name='无脑死拿资金线', line=dict(color='gray', width=1.5, dash='dash')))
            fig_all.add_trace(go.Scatter(x=df.index, y=df['Eq_Left'], mode='lines', name='左侧抄底资金线', line=dict(color='orange', width=2)))
            fig_all.add_trace(go.Scatter(x=df.index, y=df['Eq_Right'], mode='lines', name='右侧追涨资金线', line=dict(color='cyan', width=2)))
            fig_all.update_layout(title="💰 三大流派 资金曲线终极 PK 图", height=500, template="plotly_dark", hovermode="x unified")
            st.plotly_chart(fig_all, use_container_width=True)

        with tab2:
            st.subheader(f"📉 {stock_name} ({ticker}) - K线复盘")
            fig_k = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            fig_k.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K线'), row=1, col=1)
            fig_k.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='cyan', width=2), name='20日生命线'), row=1, col=1)
            fig_k.add_trace(go.Scatter(x=df.index, y=df['SMA_60'], line=dict(color='orange', width=2), name='60日牛熊线'), row=1, col=1)
            colors = ['red' if row['Open'] > row['Close'] else 'green' for index, row in df.iterrows()]
            fig_k.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='成交量'), row=2, col=1)
            fig_k.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
            fig_k.update_layout(height=600, xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_k, use_container_width=True)

        with tab3:
            st.subheader(f"🛡️ {stock_name} - 基本面雷达")
            pe = info.get('动态市盈率', '-')
            pb = info.get('市净率', '-')
            market_cap = info.get('总市值', 0) / 1e8 
            
            pe_val = float(pe) if isinstance(pe, (int, float)) and pe != '-' else 0
            pb_val = float(pb) if isinstance(pb, (int, float)) and pb != '-' else 0
            
            pe_score = 10 if pe_val <= 0 else 90 if pe_val < 15 else 60 if pe_val < 30 else max(10, 100 - (pe_val - 30))
            pb_score = 10 if pb_val <= 0 else 90 if pb_val < 2 else 60 if pb_val < 5 else max(10, 100 - (pb_val * 10))
            size_score = min(100, (market_cap / 1000) * 100) if market_cap > 0 else 10
            
            st.markdown(f"- **总市值:** {market_cap:.2f} 亿元")
            st.markdown(f"- **动态市盈率 (PE):** {pe}")
            st.markdown(f"- **市净率 (PB):** {pb}")
    else:
        st.error("无法获取数据，请检查网络或更换股票代码。")
else:
    with tab1: st.info("👈 请在左侧选择标的并点击启动回测。")

# ==========================================
# TAB 4: 组合相关性热力图
# ==========================================
with tab4:
    st.markdown("### 🔍 投资组合防暴雷检测系统 (独立运算)")
    all_stocks_pool = {
        "中国银行": "601988", "中国海油": "600938", "小米集团": "1810", 
        "比亚迪": "002594", "中远海能": "600026", "紫金矿业": "601899"
    }
    selected_assets = st.multiselect("📝 选择检测资产", options=list(all_stocks_pool.keys()), default=list(all_stocks_pool.keys()))
    corr_period = st.selectbox("📅 统计周期", ["近半年", "近1年", "近2年"], index=1)

    if st.button("🔥 生成相关性矩阵", type="primary"):
        with st.spinner("正在并发抓取收盘价..."):
            p_map = {"近半年": "6mo", "近1年": "1y", "近2年": "2y"}
            price_dict = {}
            for name in selected_assets:
                yf_ticker = get_yf_ticker(all_stocks_pool[name])
                df_s = yf.Ticker(yf_ticker).history(period=p_map.get(corr_period, "1y"))
                if not df_s.empty:
                    df_s.reset_index(inplace=True)
                    date_col = 'Date' if 'Date' in df_s.columns else 'Datetime'
                    df_s['Date'] = pd.to_datetime(df_s[date_col]).dt.tz_localize(None)
                    df_s.set_index('Date', inplace=True)
                    price_dict[name] = pd.to_numeric(df_s['Close'], errors='coerce')

            if price_dict:
                portfolio_df = pd.DataFrame(price_dict).dropna()
                fig_corr = px.imshow(portfolio_df.corr(), text_auto=".2f", aspect="auto", color_continuous_scale="RdBu_r", zmin=-1, zmax=1)
                st.plotly_chart(fig_corr, use_container_width=True)

# ==========================================
# TAB 5: 组合压力测试 (盘石计划)
# ==========================================
with tab5:
    st.subheader("🏗️ “盘石计划”组合兵棋推演 (5年极限压力测试)")
    panshi_pool = {"中国银行 (死拿)": "601988", "中国海油 (死拿)": "600938", "小米集团 (右侧)": "1810", "比亚迪 (右侧)": "002594", "中远海能 (右侧)": "600026", "紫金矿业 (死拿)": "601899"}
    cols = st.columns(3)
    weights = {}
    default_w = [20, 20, 20, 20, 10, 10] 
    
    for i, (name, code) in enumerate(panshi_pool.items()):
        with cols[i % 3]: weights[name] = st.slider(f"{name}", 0, 100, default_w[i])
    
    total_w = sum(weights.values())
    st.write(f"**当前总权重：{total_w}%**")
    
    if total_w != 100:
        st.error("❌ 请调整滑块，使总权重等于 100%。")
    else:
        if st.button("🔥 开始全组合压力测试", type="primary", use_container_width=True):
            with st.spinner("正在拉取 6 大重器数据，合成航母编队曲线..."):
                portfolio_results = []
                for name, weight in weights.items():
                    code = panshi_pool[name].split()[-1] 
                    df_stock = load_and_calc_data(code, "5年")
                    if not df_stock.empty:
                        strategy = "右侧" if "右侧" in name else "死拿"
                        eq = run_strategy_sim(df_stock, strategy)
                        weighted_eq = (np.array(eq) / 100000) * (weight / 100)
                        portfolio_results.append(weighted_eq)
                
                if portfolio_results:
                    min_len = min([len(r) for r in portfolio_results])
                    final_portfolio_eq = np.zeros(min_len)
                    for r in portfolio_results: final_portfolio_eq += r[:min_len]
                    
                    port_return = (final_portfolio_eq[-1] - 1) * 100
                    roll_max = pd.Series(final_portfolio_eq).cummax()
                    port_max_dd = ((final_portfolio_eq - roll_max) / roll_max).min() * 100
                    
                    st.divider()
                    c1, c2, c3 = st.columns(3)
                    c1.metric("组合预期总收益 (5年)", f"{port_return:.2f}%")
                    c2.metric("组合最大回撤", f"{port_max_dd:.2f}%", delta_color="inverse")
                    c3.metric("风险收益比", f"{abs(port_return/port_max_dd):.2f}" if port_max_dd != 0 else "N/A")
                    
                    fig_port = go.Figure()
                    fig_port.add_trace(go.Scatter(y=final_portfolio_eq, mode='lines', line=dict(color='limegreen', width=3)))
                    fig_port.update_layout(title="📈 盘石计划组合模拟净值", height=500, template="plotly_dark")
                    st.plotly_chart(fig_port, use_container_width=True)
