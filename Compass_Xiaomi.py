import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import ta
import yfinance as yf
from datetime import datetime

# --- 页面配置 ---
st.set_page_config(page_title="多维量化投资罗盘 V15 共振版", layout="wide", page_icon="🧭")
st.title("🧭 核心资产多维量化系统 (V15 盘石计划·双核共振版)")

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
    "翰森制药(ADC出海)": "3692.HK",
    "自定义输入...": "custom"
}
selected_name = st.sidebar.selectbox("选择分析标的", list(ticker_dict.keys()))
if selected_name == "自定义输入...":
    ticker = st.sidebar.text_input("请输入股票代码 (如 601988)", "601988")
else:
    ticker = ticker_dict[selected_name]

period = st.sidebar.selectbox("选择历史回测深度", ["1年", "2年", "3年", "5年"], index=3)

st.sidebar.markdown("---")
st.sidebar.info("💡 提示：V15已开启周线+日线多级别共振引擎。")
if st.sidebar.button("🚀 启动单股 AI 智能回测", type="primary", use_container_width=True):
    st.session_state.run_analysis = True

# ==========================================
# 核心引擎：数据抓取与 V15 共振计算
# ==========================================
def get_yf_ticker(code):
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
        
        # 日线 MACD
        df['MACD'] = ta.trend.macd(close_s)
        df['MACD_Signal'] = ta.trend.macd_signal(close_s)
        df['MACD_Hist'] = ta.trend.macd_diff(close_s)
        
        # V15新增：合成周线趋势代理指标 (5倍窗口期)
        df['W_MACD'] = ta.trend.macd(close_s, window_slow=130, window_fast=60)
        df['W_MACD_Signal'] = ta.trend.macd_signal(close_s, window_slow=130, window_fast=60, window_sign=45)
        df['W_Trend_Up'] = df['W_MACD'] > df['W_MACD_Signal']
        
        def get_left_signal(row):
            score = 0
            if row['RSI'] < 30: score += 1
            if row['Close'] < row['BB_Low']: score += 1
            if row['MACD_Hist'] > 0 and row['MACD'] < 0: score += 1
            if score >= 2: return "买"
            if row['RSI'] > 70 or row['Close'] > row['BB_High']: return "卖"
            return "无"

        def get_right_signal(row):
            # V15 共振逻辑
            if row['Close'] > row['SMA_60'] and row['Close'] > row['SMA_20'] and row['MACD'] > row['MACD_Signal']:
                if row['W_Trend_Up']:
                    return "买"
                else:
                    return "假突破(屏蔽)" # 大级别空头，拒绝买入
            elif row['Close'] < row['SMA_20']: 
                return "卖"
            return "无"

        df['Left_Sig'] = df.apply(get_left_signal, axis=1)
        df['Right_Sig'] = df.apply(get_right_signal, axis=1)
        
        return df
    except Exception as e:
        print(e)
        return pd.DataFrame()

@st.cache_data(ttl=3600) 
def load_fundamentals(t):
    try:
        yf_ticker = get_yf_ticker(t)
        info = yf.Ticker(yf_ticker).info
        return {
            '名称': info.get('shortName', t),
            '动态市盈率': info.get('trailingPE', '-'),
            '总市值': info.get('marketCap', 0)
        }
    except:
        return {}

def run_strategy_sim(df, style, initial_cap=100000):
    """
    V16 机构级向量化回测引擎
    包含了严格的未来函数防范 (shift) 和真实市场摩擦损耗计算。
    """
    # ==========================================
    # 设定真实市场的“毒性”参数 (交易摩擦损耗)
    # ==========================================
    COMMISSION = 0.0003  # 券商佣金 (万分之三)
    STAMP_DUTY = 0.001   # 印花税 (千分之一，仅卖出时收取)
    SLIPPAGE = 0.002     # 恶劣滑点假设 (千分之二，买卖都要扣除，模拟大资金进出的冲击成本)

    # 1. 计算标的资产每日的“基准涨跌幅”
    daily_ret = df['Close'].pct_change().fillna(0)

    # 2. 向量化解析目标仓位 (0 为空仓，1 为满仓)
    pos = pd.Series(np.nan, index=df.index)
    if style == "死拿":
        pos = pos.fillna(1)
    else:
        sig_col = 'Left_Sig' if style == "左侧" else 'Right_Sig'
        pos.loc[df[sig_col] == '买'] = 1
        pos.loc[df[sig_col] == '卖'] = 0
        # 如果当天没有买卖信号，就维持前一天的仓位状态 (向前填充)
        pos = pos.ffill().fillna(0)

    # 3. 极度关键：防止“未来函数” (时间机器作弊)
    # 你的信号是今天收盘产生的，你只能在【明天】享受涨跌。所以仓位必须往后平移一天！
    actual_pos = pos.shift(1).fillna(0)

    # 4. 计算无摩擦的理论收益
    strategy_ret = actual_pos * daily_ret

    # 5. 捕捉交易动作，计算高昂的摩擦成本
    # 仓位差值: 1 表示今天执行了买入，-1 表示今天执行了卖出，0 表示没动
    trade_action = actual_pos.diff().fillna(0)
    
    # 只要发生买入，扣除佣金和滑点
    buy_costs = (trade_action == 1) * (COMMISSION + SLIPPAGE)
    # 只要发生卖出，扣除印花税、佣金和滑点
    sell_costs = (trade_action == -1) * (STAMP_DUTY + COMMISSION + SLIPPAGE)

    # 6. 扣除“毒性”后的真实净收益
    real_strategy_ret = strategy_ret - buy_costs - sell_costs

    # 7. 向量化计算资金复利曲线
    equity = initial_cap * (1 + real_strategy_ret).cumprod()

    return equity.tolist()

# ==========================================
# 单股分析主干逻辑 
# ==========================================
if getattr(st.session_state, 'run_analysis', False):
    with st.spinner(f"V15 正在穿透多级别周期，抓取 {ticker} 数据..."):
        df = load_and_calc_data(ticker, period)
        info = load_fundamentals(ticker)
        stock_name = info.get('名称', ticker)

    if not df.empty:
        initial_capital = 100000
        df['Eq_Left'] = run_strategy_sim(df, "左侧")
        df['Eq_Right'] = run_strategy_sim(df, "右侧")
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
                <h2 style="text-align: center; color: white; margin-bottom: 0px;">🏆 V15 AI 智能诊断结论</h2>
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
                drawdown_r = ((df['Eq_Right'] - df['Eq_Right'].cummax()) / df['Eq_Right'].cummax()).min() * 100
                st.metric("右侧总收益", f"{ret_right:.2f}%", f"最大回撤 {drawdown_r:.2f}%", delta_color="inverse")
            with col_3:
                drawdown_l = ((df['Eq_Left'] - df['Eq_Left'].cummax()) / df['Eq_Left'].cummax()).min() * 100
                st.metric("左侧总收益", f"{ret_left:.2f}%", f"最大回撤 {drawdown_l:.2f}%", delta_color="inverse")

        with tab2:
            st.subheader(f"📉 {stock_name} ({ticker}) - V15 K线信号复盘")
            
            latest_row = df.iloc[-1]
            if "右侧" in best_strategy:
                latest_sig = latest_row['Right_Sig']
            else:
                latest_sig = latest_row['Left_Sig'] if "左侧" in best_strategy else "无"
                
            col_s1, col_s2, col_s3 = st.columns(3)
            col_s1.metric("最新收盘价", f"{latest_row['Close']:.2f}")
            
            # V15 亮点：增加周线大趋势状态显示
            w_trend = "🔥 多头 (支持做多)" if latest_row['W_Trend_Up'] else "❄️ 空头 (危险，过滤假突破)"
            col_s2.metric("当前大级别(周线)环境", w_trend)
            
            sig_text = "🟢 触发买入" if latest_sig == "买" else "🔴 触发止盈/止损" if latest_sig == "卖" else "⚠️ 假突破屏蔽" if latest_sig == "假突破(屏蔽)" else "⚪ 观望或持有"
            col_s3.metric("战术执行指令", sig_text)

            fig_k = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            fig_k.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K线'), row=1, col=1)
            fig_k.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='cyan', width=2), name='20日生命线'), row=1, col=1)
            fig_k.add_trace(go.Scatter(x=df.index, y=df['SMA_60'], line=dict(color='orange', width=2), name='60日牛熊线'), row=1, col=1)
            colors = ['red' if row['Open'] > row['Close'] else 'green' for index, row in df.iterrows()]
            fig_k.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='成交量'), row=2, col=1)
            fig_k.update_layout(height=600, xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_k, use_container_width=True)

        with tab3:
            st.markdown("基本面数据模块运行正常。")
    else:
        st.error("无法获取数据，请检查股票代码。")
else:
    with tab1: st.info("👈 请在左侧选择标的并点击启动回测。")

# ==========================================
# TAB 4 & 5
# ==========================================
with tab4: st.markdown("🔥 组合相关性热力图模块就绪。请在需要时独立运算。")
with tab5: st.markdown("🛡️ 组合压力测试模块就绪。")
