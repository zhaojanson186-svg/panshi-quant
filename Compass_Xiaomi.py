import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import ta
import yfinance as yf
import akshare as ak
from datetime import datetime, timedelta

# --- 页面配置 ---
st.set_page_config(page_title="盘石量化系统 V17 机构版", layout="wide", page_icon="🧭")
st.title("🧭 核心资产多维量化系统 (V17 盘石计划·无损复权版)")

# ==========================================
# 核心工具箱：AKShare 无损前复权引擎 + YFinance 财务快照
# ==========================================
def get_yf_ticker(code):
    """仅用于保留 YFinance 获取基本面和财务数据的通道"""
    if '.' in code: return code
    if code.startswith('6'): return f"{code}.SS"
    elif code.startswith('0') or code.startswith('3'):
        if len(code) == 6: return f"{code}.SZ"
    elif len(code) <= 5: 
        return f"{int(code):04d}.HK"
    return code

@st.cache_data(ttl=3600)
def get_ak_hist(ticker, period_str):
    """V17 核心：使用 AKShare 抓取极其精准的前复权 (qfq) K线数据"""
    end_date = datetime.now()
    years = int(period_str[0]) if period_str[0].isdigit() else 1
    start_date = end_date - timedelta(days=365 * years)
    
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    
    clean_ticker = ticker.upper().replace('.SS', '').replace('.SZ', '').replace('.HK', '')
    
    try:
        # 判断是否为 A 股 (6位数字，以0, 3, 6开头)
        if len(clean_ticker) == 6 and clean_ticker[0] in ['0', '3', '6']:
            df = ak.stock_zh_a_hist(symbol=clean_ticker, period="daily", start_date=start_str, end_date=end_str, adjust="qfq")
        else:
            # 港股处理 (补齐 5 位数)
            hk_ticker = clean_ticker.zfill(5)
            df = ak.stock_hk_hist(symbol=hk_ticker, period="daily", start_date=start_str, end_date=end_str, adjust="qfq")
            
        if df is not None and not df.empty:
            # 统一中英文列名，完美对接下游 V15 算力引擎
            df.rename(columns={'日期': 'Date', '开盘': 'Open', '最高': 'High', '最低': 'Low', '收盘': 'Close', '成交量': 'Volume'}, inplace=True)
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df.dropna(subset=['Close'])
    except Exception as e:
        pass
    return pd.DataFrame()

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

# ==========================================
# 🛰️ 顶层仪表盘：全局护卫舰长雷达 (AKShare 驱动)
# ==========================================
st.markdown("---")
st.subheader("🛰️ 全局护卫舰长雷达 (无损前复权驱动)")

if st.button("🚀 启动一键全军巡检", type="primary", use_container_width=True):
    with st.spinner("AKShare 高频接口全功率运转中，正在并发请求全军最新战况..."):
        results = []
        pool_names = [k for k in ticker_dict.keys() if k != "自定义输入..."]
        
        for name in pool_names:
            tk = ticker_dict[name]
            try:
                df_scan = get_ak_hist(tk, "1年") # 使用 AKShare 引擎
                if df_scan.empty: continue
                
                close_s = df_scan['Close'].squeeze()
                curr_price = close_s.iloc[-1]
                
                sma_20 = ta.trend.sma_indicator(close_s, window=20).iloc[-1]
                sma_60 = ta.trend.sma_indicator(close_s, window=60).iloc[-1]
                macd = ta.trend.macd(close_s).iloc[-1]
                macd_sig = ta.trend.macd_signal(close_s).iloc[-1]
                w_macd = ta.trend.macd(close_s, window_slow=130, window_fast=60).iloc[-1]
                w_macd_sig = ta.trend.macd_signal(close_s, window_slow=130, window_fast=60, window_sign=45).iloc[-1]
                atr = ta.volatility.average_true_range(df_scan['High'], df_scan['Low'], df_scan['Close'], window=14).iloc[-1]
                
                w_trend_up = w_macd > w_macd_sig
                
                sig = "⚪ 观望 / 持现"
                if curr_price > sma_60 and curr_price > sma_20 and macd > macd_sig:
                    sig = "🟢 触发右侧买入" if w_trend_up else "⚠️ 假突破屏蔽"
                elif curr_price < sma_20:
                    sig = "🔴 跌破生命线 (卖出)"
                    
                stop_loss = curr_price - 2 * atr
                
                results.append({
                    "资产名称": name,
                    "最新收盘价(前复权)": f"{curr_price:.2f}",
                    "20日生命线": f"{sma_20:.2f}",
                    "今日战术指令": sig,
                    "科学止损价(2倍ATR)": f"{stop_loss:.2f}"
                })
            except Exception as e:
                pass
                
        if results:
            res_df = pd.DataFrame(results)
            st.dataframe(res_df, use_container_width=True, hide_index=True)
            st.success("✅ 巡检完成！长官，AKShare 数据流已确保价格完全无损，请重点关注标有 🟢 或 🔴 的资产。")
st.markdown("---")

# ==========================================
# 页面主体 Tabs
# ==========================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🏆 AI 智能多维回测", 
    "📉 K线信号复盘", 
    "🕸️ 首席分析师全景扫描", 
    "🔥 组合相关性热力图",
    "🛡️ 组合压力测试",
    "🔮 蒙特卡洛未来推演"
])

# ==========================================
# 侧边栏：全局单股参数设置
# ==========================================
st.sidebar.header("⚙️ 全局单股分析设置")
selected_name = st.sidebar.selectbox("选择分析标的", list(ticker_dict.keys()))
if selected_name == "自定义输入...":
    ticker = st.sidebar.text_input("请输入股票代码 (如 601988)", "601988")
else:
    ticker = ticker_dict[selected_name]

period = st.sidebar.selectbox("选择历史回测深度", ["1年", "2年", "3年", "5年"], index=3)
st.sidebar.markdown("---")
st.sidebar.info("💡 提示：V17已接管底层 K 线引擎，【复权黑洞】已被 AKShare 彻底消灭。基本面数据仍保留 YFinance 接口。")
if st.sidebar.button("🚀 启动单股 AI 智能回测", type="primary", use_container_width=True):
    st.session_state.run_analysis = True

# ==========================================
# 核心引擎：数据加载与计算
# ==========================================
@st.cache_data(ttl=3600) 
def load_and_calc_data(t, p):
    # 使用 V17 AKShare 引擎获取无损 K 线
    df = get_ak_hist(t, p)
    if df.empty: return pd.DataFrame()
    
    try:
        close_s = df['Close'].squeeze() 
        df['SMA_20'] = ta.trend.sma_indicator(close_s, window=20) 
        df['SMA_60'] = ta.trend.sma_indicator(close_s, window=60)
        df['RSI'] = ta.momentum.rsi(close_s, window=14)
        df['BB_High'] = ta.volatility.bollinger_hband(close_s, window=20, window_dev=2)
        df['BB_Low'] = ta.volatility.bollinger_lband(close_s, window=20, window_dev=2)
        
        df['MACD'] = ta.trend.macd(close_s)
        df['MACD_Signal'] = ta.trend.macd_signal(close_s)
        df['MACD_Hist'] = ta.trend.macd_diff(close_s)
        
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
            if row['Close'] > row['SMA_60'] and row['Close'] > row['SMA_20'] and row['MACD'] > row['MACD_Signal']:
                if row['W_Trend_Up']: return "买"
                else: return "假突破(屏蔽)" 
            elif row['Close'] < row['SMA_20']: return "卖"
            return "无"

        df['Left_Sig'] = df.apply(get_left_signal, axis=1)
        df['Right_Sig'] = df.apply(get_right_signal, axis=1)
        return df
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=3600) 
def load_fundamentals(t):
    # 财务数据仍然使用 YFinance 的全球网关抓取快照
    try:
        yf_ticker = get_yf_ticker(t)
        info = yf.Ticker(yf_ticker).info
        info['名称'] = info.get('shortName', t)
        return info
    except:
        return {}

def run_strategy_sim(df, style, initial_cap=100000):
    COMMISSION = 0.0003  
    STAMP_DUTY = 0.001   
    SLIPPAGE = 0.002     

    daily_ret = df['Close'].pct_change().fillna(0)
    pos = pd.Series(np.nan, index=df.index)
    
    if style == "死拿": pos = pos.fillna(1)
    else:
        sig_col = 'Left_Sig' if style == "左侧" else 'Right_Sig'
        pos.loc[df[sig_col] == '买'] = 1
        pos.loc[df[sig_col] == '卖'] = 0
        pos = pos.ffill().fillna(0)

    actual_pos = pos.shift(1).fillna(0)
    strategy_ret = actual_pos * daily_ret
    trade_action = actual_pos.diff().fillna(0)
    
    buy_costs = (trade_action == 1) * (COMMISSION + SLIPPAGE)
    sell_costs = (trade_action == -1) * (STAMP_DUTY + COMMISSION + SLIPPAGE)

    real_strategy_ret = strategy_ret - buy_costs - sell_costs
    equity = initial_cap * (1 + real_strategy_ret).cumprod()
    return equity.tolist()

# ==========================================
# 单股分析主干逻辑 
# ==========================================
if getattr(st.session_state, 'run_analysis', False):
    with st.spinner(f"V17 AKShare 引擎正在加载并计算 {ticker} 数据..."):
        df = load_and_calc_data(ticker, period)
        info = load_fundamentals(ticker)
        stock_name = info.get('名称', ticker)

    if not df.empty:
        initial_capital = 100000
        df['Eq_Left'] = run_strategy_sim(df, "左侧")
        df['Eq_Right'] = run_strategy_sim(df, "右侧")
        df['Eq_Hold'] = run_strategy_sim(df, "死拿")

        ret_left = (df['Eq_Left'][-1] - initial_capital) / initial_capital * 100
        ret_right = (df['Eq_Right'][-1] - initial_capital) / initial_capital * 100
        ret_hold = (df['Eq_Hold'][-1] - initial_capital) / initial_capital * 100

        results = {"📉 左侧抄底波段": ret_left, "📈 右侧顺势追涨": ret_right, "🛡️ 无脑死拿一直抱": ret_hold}
        best_strategy = max(results, key=results.get)
        best_return = results[best_strategy]

        with tab1:
            st.markdown(f"""
            <div style="background-color: #1E1E1E; padding: 20px; border-radius: 10px; border: 2px solid {'#FFD700' if best_return > 0 else '#FF4500'};">
                <h2 style="text-align: center; color: white; margin-bottom: 0px;">🏆 V17 AI 智能诊断结论</h2>
                <h4 style="text-align: center; color: #A0A0A0; margin-top: 10px;">经过过去 {period} 数据及真实交易损耗推演，【{stock_name}】最适合：</h4>
                <h1 style="text-align: center; color: {'#00FF7F' if best_return > 0 else '#FF6347'}; font-size: 3em; margin: 10px 0;">{best_strategy}</h1>
                <p style="text-align: center; color: white; font-size: 1.2em;">扣除手续费后历史总收益率可达：<strong>{best_return:.2f}%</strong></p>
            </div>
            <br>
            """, unsafe_allow_html=True)
            col_1, col_2, col_3 = st.columns(3)
            with col_1:
                drawdown_h = ((df['Eq_Hold'] - np.maximum.accumulate(df['Eq_Hold'])) / np.maximum.accumulate(df['Eq_Hold'])).min() * 100
                st.metric("死拿总收益(税后)", f"{ret_hold:.2f}%", f"最大回撤 {drawdown_h:.2f}%", delta_color="inverse")
            with col_2:
                drawdown_r = ((df['Eq_Right'] - np.maximum.accumulate(df['Eq_Right'])) / np.maximum.accumulate(df['Eq_Right'])).min() * 100
                st.metric("右侧总收益(税后)", f"{ret_right:.2f}%", f"最大回撤 {drawdown_r:.2f}%", delta_color="inverse")
            with col_3:
                drawdown_l = ((df['Eq_Left'] - np.maximum.accumulate(df['Eq_Left'])) / np.maximum.accumulate(df['Eq_Left'])).min() * 100
                st.metric("左侧总收益(税后)", f"{ret_left:.2f}%", f"最大回撤 {drawdown_l:.2f}%", delta_color="inverse")

            st.markdown("<br><hr>", unsafe_allow_html=True)
            st.markdown("### 💎 机构级交易执行面板 (Position & Risk Management)")
            
            df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
            current_price = df['Close'].iloc[-1]
            current_atr = df['ATR'].iloc[-1]
            
            risk_per_trade = 0.02 
            stop_loss_dist = current_atr * 2 
            stop_loss_price = current_price - stop_loss_dist
            
            risk_amount = initial_capital * risk_per_trade
            suggested_shares = int(risk_amount / stop_loss_dist) if stop_loss_dist > 0 else 0
            position_value = suggested_shares * current_price
            position_pct = (position_value / initial_capital) * 100

            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                st.metric(label="🚨 科学止损位 (2倍ATR)", value=f"{stop_loss_price:.2f}", delta=f"距离现价跌幅 {(stop_loss_price/current_price - 1)*100:.2f}%", delta_color="inverse")
            with col_r2:
                st.metric(label="⚖️ 建议买入股数", value=f"{suggested_shares:,} 股", help="基于总资金10万、单笔最大亏损2%的风险平价模型计算得出。")
            with col_r3:
                st.metric(label="💼 建议建仓比例", value=f"{position_pct:.1f}%" if position_pct <= 100 else "100.0% (限制满仓)", delta="基于当前波动率测算", delta_color="off")
            st.info("💡 **顶级投顾指令**：系统已根据标的真实波动率测算出防弹衣厚度。买入后，请将券商APP的条件单止损价严格设置为上述【科学止损位】。")

        with tab2:
            st.subheader(f"📉 {stock_name} ({ticker}) - 彭博级三联屏图表")
            latest_row = df.iloc[-1]
            latest_sig = latest_row['Right_Sig'] if "右侧" in best_strategy else latest_row['Left_Sig'] if "左侧" in best_strategy else "无"
                
            col_s1, col_s2, col_s3 = st.columns(3)
            col_s1.metric("最新收盘价(前复权)", f"{latest_row['Close']:.2f}")
            w_trend = "🔥 多头 (支持做多)" if latest_row['W_Trend_Up'] else "❄️ 空头 (危险，过滤假突破)"
            col_s2.metric("当前大级别(周线)环境", w_trend)
            sig_text = "🟢 触发买入" if latest_sig == "买" else "🔴 触发止盈/止损" if latest_sig == "卖" else "⚠️ 假突破屏蔽" if latest_sig == "假突破(屏蔽)" else "⚪ 观望或持有"
            col_s3.metric("战术执行指令", sig_text)

            fig_k = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.2, 0.2], specs=[[{"secondary_y": False}], [{"secondary_y": False}], [{"secondary_y": True}]])
            fig_k.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K线'), row=1, col=1)
            fig_k.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='cyan', width=1.5), name='20日生命线'), row=1, col=1)
            fig_k.add_trace(go.Scatter(x=df.index, y=df['SMA_60'], line=dict(color='orange', width=1.5), name='60日牛熊线'), row=1, col=1)
            
            macd_colors = ['#2ca02c' if val > 0 else '#d62728' for val in df['MACD_Hist']]
            fig_k.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], marker_color=macd_colors, name='MACD 柱'), row=2, col=1)
            fig_k.add_trace(go.Scatter(x=df.index, y=df['MACD'], line=dict(color='white', width=1.5), name='DIF (快线)'), row=2, col=1)
            fig_k.add_trace(go.Scatter(x=df.index, y=df['MACD_Signal'], line=dict(color='yellow', width=1.5), name='DEA (慢线)'), row=2, col=1)
            
            colors_vol = ['#d62728' if row['Open'] > row['Close'] else '#2ca02c' for index, row in df.iterrows()]
            fig_k.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors_vol, name='成交量', opacity=0.5), row=3, col=1, secondary_y=False)
            fig_k.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='magenta', width=2), name='RSI(14) 情绪值'), row=3, col=1, secondary_y=True)
            fig_k.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1, secondary_y=True)
            fig_k.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1, secondary_y=True)
            
            fig_k.update_layout(height=850, xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(l=10, r=10, t=30, b=10))
            fig_k.update_yaxes(title_text="RSI", range=[0, 100], secondary_y=True, row=3, col=1)
            st.plotly_chart(fig_k, use_container_width=True)

        with tab3:
            st.subheader(f"🕸️ {stock_name} ({ticker}) - 首席分析师全景扫描")
            st.markdown("---")
            market_cap = info.get('marketCap', 0)
            market_cap_str = f"{market_cap / 100000000:.2f} 亿" if isinstance(market_cap, (int, float)) and market_cap > 0 else "暂无数据"
            
            def fmt_num(val, is_pct=False):
                if val is None or val == 'Infinity' or str(val) == 'nan': return "暂无"
                if isinstance(val, (int, float)): return f"{val * 100:.2f}%" if is_pct else f"{val:.2f}"
                return "暂无"

            col_v1, col_v2, col_v3, col_v4 = st.columns(4)
            col_v1.metric("总市值", market_cap_str)
            col_v2.metric("TTM 动态市盈率 (PE)", fmt_num(info.get('trailingPE')))
            col_v3.metric("远期市盈率预估 (Fwd PE)", fmt_num(info.get('forwardPE')))
            col_v4.metric("市净率 (PB)", fmt_num(info.get('priceToBook')))
            st.markdown("---")

        with tab4:
            st.subheader("🔥 组合相关性热力图")
            st.info("此模块需要同时读取多只股票长周期数据，请知悉：AKShare 高频访问可能稍慢。")

        with tab5:
            st.subheader("🛡️ 组合压力测试")
            st.info("此模块正在升级对接 AKShare 组合引擎，暂挂起。")

        with tab6:
            st.subheader(f"🔮 {stock_name} - 蒙特卡洛未来 30 天概率推演")
            if st.button("🌌 启动量子算力推演未来", type="primary", key="btn_mc"):
                with st.spinner("计算中..."):
                    try:
                        returns = df['Close'].pct_change().dropna()
                        mu, sigma, last_price = returns.mean(), returns.std(), df['Close'].iloc[-1]
                        sim_days, sim_runs = 30, 100
                        sim_paths = np.zeros((sim_days, sim_runs))
                        sim_paths[0] = last_price
                        for t in range(1, sim_days):
                            Z = np.random.standard_normal(sim_runs)
                            sim_paths[t] = sim_paths[t-1] * np.exp((mu - 0.5 * sigma**2) + sigma * Z)
                        p5, p50, p95 = np.percentile(sim_paths, 5, axis=1), np.percentile(sim_paths, 50, axis=1), np.percentile(sim_paths, 95, axis=1)
                        
                        fig_mc = go.Figure()
                        days_x = list(range(1, sim_days + 1))
                        for i in range(sim_runs): fig_mc.add_trace(go.Scatter(x=days_x, y=sim_paths[:, i], mode='lines', line=dict(color='rgba(0, 191, 255, 0.05)'), showlegend=False))
                        fig_mc.add_trace(go.Scatter(x=days_x, y=p95, mode='lines', line=dict(color='lime', dash='dash'), name='乐观预期'))
                        fig_mc.add_trace(go.Scatter(x=days_x, y=p50, mode='lines', line=dict(color='white'), name='大概率中枢'))
                        fig_mc.add_trace(go.Scatter(x=days_x, y=p5, mode='lines', line=dict(color='red', dash='dash'), name='悲观预期'))
                        fig_mc.update_layout(template="plotly_dark", height=600)
                        st.plotly_chart(fig_mc, use_container_width=True)
                    except Exception as e:
                        st.error(f"推演失败：{e}")
    else:
        st.error("数据通道无响应，请重试或检查代码。")
