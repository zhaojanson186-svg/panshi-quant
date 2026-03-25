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
st.set_page_config(page_title="盘石量化系统 V16 机构版", layout="wide", page_icon="🧭")
st.title("🧭 核心资产多维量化系统 (V16 盘石计划·机构终极版)")

# ==========================================
# 核心工具箱 (必须放在最前面，让后面的雷达能用到)
# ==========================================
def get_yf_ticker(code):
    if '.' in code: return code
    if code.startswith('6'): return f"{code}.SS"
    elif code.startswith('0') or code.startswith('3'):
        if len(code) == 6: return f"{code}.SZ"
    elif len(code) <= 5: 
        return f"{int(code):04d}.HK"
    return code

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
# 🛰️ 顶层仪表盘：全局护卫舰长雷达
# ==========================================
st.markdown("---")
st.subheader("🛰️ 全局护卫舰长雷达 (午休 10 秒盯盘专用)")

if st.button("🚀 启动一键全军巡检", type="primary", use_container_width=True):
    with st.spinner("雷达全功率运转中，正在并发请求全军最新战况..."):
        results = []
        pool_names = [k for k in ticker_dict.keys() if k != "自定义输入..."]
        
        for name in pool_names:
            tk = ticker_dict[name]
            yf_tk = get_yf_ticker(tk)
            try:
                df_scan = yf.Ticker(yf_tk).history(period="1y")
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
                    "最新收盘价": f"{curr_price:.2f}",
                    "20日生命线": f"{sma_20:.2f}",
                    "今日战术指令": sig,
                    "科学止损价(2倍ATR)": f"{stop_loss:.2f}"
                })
            except Exception as e:
                pass
                
        if results:
            res_df = pd.DataFrame(results)
            st.dataframe(res_df, use_container_width=True, hide_index=True)
            st.success("✅ 巡检完成！长官，请重点关注标有 🟢 或 🔴 的资产，其余可安心略过。")
st.markdown("---")

# ==========================================
# 页面主体 Tabs
# ==========================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🏆 AI 智能多维回测", 
    "📉 K线信号复盘", 
    "🕸️ 首席分析师全景扫描", 
    "🔥 组合相关性热力图",
    "🛡️ 组合压力测试 (盘石计划)",
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
st.sidebar.info("💡 提示：V16已开启【周线级别共振过滤】及【真实交易滑点与手续费扣除】。")
if st.sidebar.button("🚀 启动单股 AI 智能回测", type="primary", use_container_width=True):
    st.session_state.run_analysis = True

# ==========================================
# 核心引擎：数据抓取与 V15 共振计算
# ==========================================
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
    with st.spinner(f"V16 引擎正在加载并计算 {ticker} 数据..."):
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
                <h2 style="text-align: center; color: white; margin-bottom: 0px;">🏆 V16 AI 智能诊断结论</h2>
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

            # 💎 顶级投顾引擎：ATR 动态风控与仓位计算器
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
            st.subheader(f"📉 {stock_name} ({ticker}) - V16 K线信号复盘")
            latest_row = df.iloc[-1]
            latest_sig = latest_row['Right_Sig'] if "右侧" in best_strategy else latest_row['Left_Sig'] if "左侧" in best_strategy else "无"
                
            col_s1, col_s2, col_s3 = st.columns(3)
            col_s1.metric("最新收盘价", f"{latest_row['Close']:.2f}")
            w_trend = "🔥 多头 (支持做多)" if latest_row['W_Trend_Up'] else "❄️ 空头 (危险，过滤假突破)"
            col_s2.metric("当前大级别(周线)环境", w_trend)
            sig_text = "🟢 触发买入" if latest_sig == "买" else "🔴 触发止盈/止损" if latest_sig == "卖" else "⚠️ 假突破屏蔽" if latest_sig == "假突破(屏蔽)" else "⚪ 观望或持有"
            col_s3.metric("战术执行指令", sig_text)

           # ==========================================
            # 📊 彭博级三联屏图表 (K线 + MACD + Vol/RSI)
            # ==========================================
            fig_k = make_subplots(
                rows=3, cols=1, 
                shared_xaxes=True, 
                vertical_spacing=0.03, 
                row_heights=[0.6, 0.2, 0.2],
                specs=[[{"secondary_y": False}], [{"secondary_y": False}], [{"secondary_y": True}]]
            )
            
            # 1. 顶层主图：K线与生命线
            fig_k.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K线'), row=1, col=1)
            fig_k.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='cyan', width=1.5), name='20日生命线'), row=1, col=1)
            fig_k.add_trace(go.Scatter(x=df.index, y=df['SMA_60'], line=dict(color='orange', width=1.5), name='60日牛熊线'), row=1, col=1)
            
            # 2. 中层副图：MACD 动量共振
            macd_colors = ['#2ca02c' if val > 0 else '#d62728' for val in df['MACD_Hist']]
            fig_k.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], marker_color=macd_colors, name='MACD 柱'), row=2, col=1)
            fig_k.add_trace(go.Scatter(x=df.index, y=df['MACD'], line=dict(color='white', width=1.5), name='DIF (快线)'), row=2, col=1)
            fig_k.add_trace(go.Scatter(x=df.index, y=df['MACD_Signal'], line=dict(color='yellow', width=1.5), name='DEA (慢线)'), row=2, col=1)
            
            # 3. 底层副图：成交量与 RSI 情绪雷达 (双Y轴)
            colors_vol = ['#d62728' if row['Open'] > row['Close'] else '#2ca02c' for index, row in df.iterrows()]
            fig_k.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors_vol, name='成交量', opacity=0.5), row=3, col=1, secondary_y=False)
            
            # 叠加 RSI 情绪紫线
            fig_k.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='magenta', width=2), name='RSI(14) 情绪值'), row=3, col=1, secondary_y=True)
            # 画出 RSI 的极度冰点和沸点预警线
            fig_k.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1, secondary_y=True, annotation_text="超买区 (危险)")
            fig_k.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1, secondary_y=True, annotation_text="超卖区 (机会)")
            
            # 美化界面布局
            fig_k.update_layout(height=850, xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(l=10, r=10, t=30, b=10))
            fig_k.update_yaxes(title_text="RSI (0-100)", range=[0, 100], secondary_y=True, row=3, col=1)
            
            st.plotly_chart(fig_k, use_container_width=True)
            st.info("💡 **投顾读图指南**：第一眼看顶层 K 线是否站上蓝线(20日)；第二眼看中层 MACD 柱子是否翻绿(多头)；第三眼看底层 RSI 紫线是否从绿色虚线(30冰点)反弹。三者共振，即为重仓出击之时！")

        with tab3:
            st.subheader(f"🕸️ {stock_name} ({ticker}) - 首席分析师全景扫描")
            st.markdown("---")
            
            market_cap = info.get('marketCap', 0)
            market_cap_str = f"{market_cap / 100000000:.2f} 亿" if isinstance(market_cap, (int, float)) and market_cap > 0 else "暂无数据"
            
            def fmt_num(val, is_pct=False):
                if val is None or val == 'Infinity' or str(val) == 'nan': return "暂无"
                if isinstance(val, (int, float)): return f"{val * 100:.2f}%" if is_pct else f"{val:.2f}"
                return "暂无"

            st.markdown("#### ⚖️ 核心估值模型 (Valuation)")
            col_v1, col_v2, col_v3, col_v4 = st.columns(4)
            col_v1.metric("总市值", market_cap_str)
            col_v2.metric("TTM 动态市盈率 (PE)", fmt_num(info.get('trailingPE')))
            col_v3.metric("远期市盈率预估 (Fwd PE)", fmt_num(info.get('forwardPE')))
            col_v4.metric("市净率 (PB)", fmt_num(info.get('priceToBook')))
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("#### 💰 盈利能力与护城河 (Profitability)")
            col_p1, col_p2, col_p3, col_p4 = st.columns(4)
            col_p1.metric("净资产收益率 (ROE)", fmt_num(info.get('returnOnEquity'), True))
            col_p2.metric("总资产收益率 (ROA)", fmt_num(info.get('returnOnAssets'), True))
            col_p3.metric("销售毛利率 (Gross Margin)", fmt_num(info.get('grossMargins'), True))
            col_p4.metric("销售净利率 (Net Margin)", fmt_num(info.get('profitMargins'), True))
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("#### 🚀 成长性与安全边际 (Growth & Risk)")
            col_g1, col_g2, col_g3, col_g4 = st.columns(4)
            col_g1.metric("季度营收同比增速", fmt_num(info.get('revenueGrowth'), True))
            col_g2.metric("季度利润同比增速", fmt_num(info.get('earningsGrowth'), True))
            col_g3.metric("股息率 (Dividend Yield)", fmt_num(info.get('dividendYield'), True))
            
            high_52 = info.get('fiftyTwoWeekHigh')
            low_52 = info.get('fiftyTwoWeekLow')
            curr_price = info.get('currentPrice') or info.get('regularMarketPrice')
            range_str = "暂无"
            if all(isinstance(x, (int, float)) for x in [high_52, low_52, curr_price]) and high_52 > low_52:
                pos = (curr_price - low_52) / (high_52 - low_52) * 100
                range_str = f"价格分位: {pos:.1f}%"
            col_g4.metric("52周价格水位线", range_str, f"最低 {fmt_num(low_52)} / 最高 {fmt_num(high_52)}")
            
            st.markdown("---")
            st.markdown("### 🧠 AI 首席分析师体检报告")
            
            analysis_text = []
            pe = info.get('trailingPE')
            if isinstance(pe, (int, float)):
                if pe < 0: analysis_text.append("⚠️ **【估值预警】**：公司目前处于亏损状态 (市盈率为负)。")
                elif pe < 15: analysis_text.append("🟢 **【估值极具吸引力】**：当前动态市盈率极低 (<15倍)。存在左侧‘捡漏’的巨大潜力。")
                elif pe > 50: analysis_text.append("🔴 **【高估值溢价】**：市盈率极高 (>50倍)！需警惕杀估值风险。")
                else: analysis_text.append("⚪ **【估值处于合理中枢】**：市盈率处于 15-50 倍的常规区间。")

            roe = info.get('returnOnEquity')
            gross_margin = info.get('grossMargins')
            if isinstance(roe, (int, float)) and roe > 0.15: analysis_text.append("🔥 **【极强护城河】**：净资产收益率 (ROE) 超过 15%！说明公司具备极强的自我造血能力。")
            elif isinstance(roe, (int, float)) and roe < 0.05: analysis_text.append("⚠️ **【造血能力疲软】**：ROE 偏低 (<5%)，资金利用效率不高。")

            if isinstance(gross_margin, (int, float)) and gross_margin > 0.60: analysis_text.append("💊 **【印钞机属性】**：销售毛利率超过 60%！具备极强定价权。")
            elif isinstance(gross_margin, (int, float)) and gross_margin < 0.15: analysis_text.append("🧱 **【苦哈哈的辛苦钱】**：毛利率低于 15%，典型的薄利多销。")

            div = info.get('dividendYield')
            if isinstance(div, (int, float)) and div > 0.04: analysis_text.append("🛡️ **【无敌现金牛】**：股息率高达 4% 以上，是极佳的底仓防御品种。")

            if not analysis_text: st.warning("暂无足够的基本面数据生成 AI 体检报告。")
            else:
                for text in analysis_text:
                    if "🟢" in text or "🔥" in text or "💊" in text or "🛡️" in text: st.success(text)
                    elif "⚠️" in text: st.warning(text)
                    elif "🔴" in text: st.error(text)
                    else: st.info(text)

    else:
        st.error("无法获取数据，请检查股票代码。")
else:
    with tab1: st.info("👈 请在左侧选择标的并点击启动回测。")

# ==========================================
# 组合管理模块：Tab 4 (相关性) 与 Tab 5 (压力测试)
# ==========================================
with tab4:
    st.subheader("🔥 盘石组合 - 资产相关性热力图 (风险隔离鉴定)")
    st.markdown("**数值越接近 1，说明同涨同跌；接近 0 或负数，说明具备极佳的风险对冲（防弹衣）效果。**")
    
    if st.button("📊 生成组合相关性矩阵", key="btn_corr", type="primary"):
        with st.spinner("正在抽取全军数据，计算皮尔逊相关系数..."):
            try:
                rename_dict = {get_yf_ticker(v): k.split('(')[0] for k, v in ticker_dict.items() if v != "custom"}
                pool_tickers = list(rename_dict.keys())
                data = yf.download(pool_tickers, period="1y", progress=False)['Close']
                data.rename(columns=rename_dict, inplace=True)
                
                corr_matrix = data.pct_change().corr()
                fig_corr = px.imshow(corr_matrix, text_auto=".2f", color_continuous_scale="RdBu_r", zmin=-1, zmax=1, aspect="auto")
                fig_corr.update_layout(template="plotly_dark", height=600)
                st.plotly_chart(fig_corr, use_container_width=True)
            except Exception as e:
                st.error(f"计算失败，请检查网络或股票代码：{e}")

with tab5:
    st.subheader("🛡️ 盘石组合 - 极端压力测试 (历史最大回撤)")
    st.markdown("模拟测试：在过去一年中，如果将资金**等权重分散**买入上述所有核心资产，你的账户净值需要承受的最大打击是多少？")
    
    if st.button("🌪️ 启动黑天鹅压力测试", key="btn_stress", type="primary"):
        with st.spinner("正在模拟极端市场环境..."):
            try:
                pool_tickers = [get_yf_ticker(v) for k, v in ticker_dict.items() if v != "custom"]
                data = yf.download(pool_tickers, period="1y", progress=False)['Close']
                daily_returns = data.pct_change().fillna(0)
                
                port_return = daily_returns.mean(axis=1)
                cum_return = (1 + port_return).cumprod()
                rolling_max = cum_return.cummax()
                drawdown = (cum_return - rolling_max) / rolling_max
                max_drawdown = drawdown.min() * 100
                
                col_st1, col_st2 = st.columns(2)
                col_st1.metric("盘石组合近 1 年累计收益", f"{(cum_return.iloc[-1] - 1)*100:.2f}%")
                col_st2.metric("遭遇的历史最大回撤", f"{max_drawdown:.2f}%", delta_color="inverse")
                
                fig_dd = go.Figure()
                fig_dd.add_trace(go.Scatter(x=drawdown.index, y=drawdown*100, fill='tozeroy', fillcolor='rgba(255, 69, 0, 0.3)', line=dict(color='orangered'), name='资金回撤 (%)'))
                fig_dd.update_layout(title="组合资金水位图 (Underwater Chart)", template="plotly_dark", height=400)
                st.plotly_chart(fig_dd, use_container_width=True)
            except Exception as e:
                st.error(f"压力测试失败：{e}")
                # ==========================================
# 🔮 终极武器：Tab 6 蒙特卡洛未来推演引擎
# ==========================================
if getattr(st.session_state, 'run_analysis', False) and not df.empty:
    with tab6:
        st.subheader(f"🔮 {stock_name} ({ticker}) - 蒙特卡洛未来 30 天概率推演")
        st.markdown("基于 **几何布朗运动 (GBM)** 算法，结合该资产过去一年的历史波动率与收益率均值，引入随机游走变量，模拟出 **100 种可能的未来平行宇宙**。")
        
        if st.button("🌌 启动量子算力推演未来", type="primary", key="btn_mc"):
            with st.spinner("正在调用蒙特卡洛引擎，疯狂计算平行宇宙的 100 条折叠时间线..."):
                try:
                    # 1. 提取资产的“基因特征” (波动率与预期收益)
                    returns = df['Close'].pct_change().dropna()
                    mu = returns.mean()
                    sigma = returns.std()
                    last_price = df['Close'].iloc[-1]
                    
                    # 2. 设定推演参数
                    sim_days = 30 # 推演未来 30 个交易日
                    sim_runs = 100 # 模拟 100 种平行宇宙
                    
                    # 3. 核心算法：几何布朗运动 (S_t = S_{t-1} * exp((mu - sigma^2/2) + sigma * Z))
                    sim_paths = np.zeros((sim_days, sim_runs))
                    sim_paths[0] = last_price
                    
                    for t in range(1, sim_days):
                        # Z 为标准正态分布的随机游走
                        Z = np.random.standard_normal(sim_runs)
                        sim_paths[t] = sim_paths[t-1] * np.exp((mu - 0.5 * sigma**2) + sigma * Z)
                        
                    # 4. 数据统计与百分位提取
                    p5 = np.percentile(sim_paths, 5, axis=1)   # 极度悲观线 (底线)
                    p50 = np.percentile(sim_paths, 50, axis=1) # 大概率中枢线
                    p95 = np.percentile(sim_paths, 95, axis=1) # 极度乐观线 (天花板)
                    
                    # 5. 绘制震撼的概率云图谱
                    fig_mc = go.Figure()
                    days_x = list(range(1, sim_days + 1))
                    
                    # 画出 100 条幽灵般的平行宇宙轨迹
                    for i in range(sim_runs):
                        fig_mc.add_trace(go.Scatter(x=days_x, y=sim_paths[:, i], mode='lines', line=dict(color='rgba(0, 191, 255, 0.05)'), showlegend=False, hoverinfo='skip'))
                        
                    # 画出三根核心概率线
                    fig_mc.add_trace(go.Scatter(x=days_x, y=p95, mode='lines', line=dict(color='lime', width=2, dash='dash'), name='乐观预期 (Top 5%)'))
                    fig_mc.add_trace(go.Scatter(x=days_x, y=p50, mode='lines', line=dict(color='white', width=3), name='大概率中枢 (中位数)'))
                    fig_mc.add_trace(go.Scatter(x=days_x, y=p5, mode='lines', line=dict(color='red', width=2, dash='dash'), name='悲观预期 (Bottom 5%)'))
                    
                    fig_mc.update_layout(title=f"{stock_name} 蒙特卡洛 30 天路径推演图谱", template="plotly_dark", height=600, xaxis_title="未来天数 (交易日)", yaxis_title="预测价格")
                    st.plotly_chart(fig_mc, use_container_width=True)
                    
                    # 6. 提取 30 天后的最终审判数据
                    end_p50 = p50[-1]
                    end_p95 = p95[-1]
                    end_p5 = p5[-1]
                    
                    col_m1, col_m2, col_m3 = st.columns(3)
                    col_m1.metric("⚖️ 30天后中性预期 (中枢)", f"{end_p50:.2f}", f"{(end_p50/last_price - 1)*100:.2f}%")
                    col_m2.metric("🚀 30天后极度乐观 (天花板)", f"{end_p95:.2f}", f"{(end_p95/last_price - 1)*100:.2f}%")
                    col_m3.metric("🩸 30天后极度悲观 (底线)", f"{end_p5:.2f}", f"{(end_p5/last_price - 1)*100:.2f}%", delta_color="inverse")
                    
                    st.info("💡 **顶级基金经理内参**：不要做算命先生，要做概率玩家！[蒙特卡洛模拟] 告诉你的是【赔率分布】。如果图中的【极度悲观线】跌破了你的止损位，或者让你夜不能寐，说明当前的仓位超出了你的心脏负荷，请立刻减仓！反之，如果大概率中枢稳步向上，闭上眼睛，让利润奔跑。")
                except Exception as e:
                    st.error(f"算力引擎过载，推演失败：{e}")
