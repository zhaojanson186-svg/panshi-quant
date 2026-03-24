import yfinance as yf
import pandas as pd
import ta
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr  
import os
from datetime import datetime

# ==========================================
# 1. 邮箱基础配置
# ==========================================
SENDER_EMAIL = os.environ.get('SENDER_EMAIL')      
SENDER_PWD = os.environ.get('SENDER_PASSWORD')     
RECEIVER_EMAIL = os.environ.get('RECEIVER_EMAIL')  
SMTP_SERVER = "smtp.qq.com"  
SMTP_PORT = 465              

# ==========================================
# 2. 盘石计划标的池与策略基因
# ==========================================
panshi_pool = {
    "中国银行": {"code": "601988.SS", "strategy": "死拿"},
    "中国海油": {"code": "600938.SS", "strategy": "死拿"},
    "小米集团": {"code": "1810.HK", "strategy": "右侧"},
    "比亚迪":   {"code": "002594.SZ", "strategy": "右侧"},
    "中远海能": {"code": "600026.SS", "strategy": "右侧"},
    "紫金矿业": {"code": "601899.SS", "strategy": "死拿"},
    "翰森制药": {"code": "3692.HK", "strategy": "右侧"} # <--- 新加这行！
}


# ==========================================
# 3. V15 核心计算引擎 (周线+日线多维共振)
# ==========================================
def check_signals():
    alert_messages = []
    date_str = datetime.now().strftime("%Y-%m-%d") 
    
    for name, info in panshi_pool.items():
        if info['strategy'] == "死拿":
            continue 
            
        try:
            # 抓取过去2年的数据，确保周线计算有足够的 K 线积淀
            df = yf.Ticker(info['code']).history(period="2y")
            if df.empty: continue
            
            # --- 步骤 A: 计算日线级别指标 ---
            close_s = df['Close'].squeeze()
            df['SMA_20'] = ta.trend.sma_indicator(close_s, window=20)
            df['SMA_60'] = ta.trend.sma_indicator(close_s, window=60)
            df['MACD'] = ta.trend.macd(close_s)
            df['MACD_Signal'] = ta.trend.macd_signal(close_s)
            
            # --- 步骤 B: 降维打击，合成周线级别数据 ---
            # 按周五重采样，合成真实的周K线
            df_weekly = df.resample('W-FRI').agg({'Close': 'last'})
            df_weekly['W_MACD'] = ta.trend.macd(df_weekly['Close'])
            df_weekly['W_MACD_Signal'] = ta.trend.macd_signal(df_weekly['Close'])
            # 判断周线趋势：周线MACD大于信号线，视为大级别多头
            df_weekly['W_Trend_Up'] = df_weekly['W_MACD'] > df_weekly['W_MACD_Signal']
            
            # --- 步骤 C: 提取最新一天的状态 ---
            latest_daily = df.iloc[-1] 
            date_str = df.index[-1].strftime("%Y-%m-%d")
            close_price = latest_daily['Close']
            
            # 提取大级别（周线）的宏观态度
            latest_weekly_trend = df_weekly.iloc[-1]['W_Trend_Up']
            
            signal = "⚪ 观望持有"
            
            # --- 步骤 D: 共振过滤与审判 ---
            if close_price > latest_daily['SMA_60'] and close_price > latest_daily['SMA_20'] and latest_daily['MACD'] > latest_daily['MACD_Signal']:
                if latest_weekly_trend:
                    signal = "🟢 触发【右侧买入】信号 (日线突破且周线MACD共振向上，大趋势确认)"
                else:
                    signal = "⚠️ 触发屏蔽机制 (日线虽突破，但周线处于空头趋势，防范假突破噪音，建议放弃交易)"
                    
            elif close_price < latest_daily['SMA_20']:
                # 卖出不需要周线共振：防守防线破裂，直接跑
                signal = "🔴 触发【卖出/止损】信号 (跌破日线20日防守，无条件避险出局)"
                
            if "🟢" in signal or "🔴" in signal or "⚠️" in signal:
                msg = f"【{name}】 最新收盘价: {close_price:.2f}\n   指令: {signal}"
                alert_messages.append(msg)
                
        except Exception as e:
            print(f"获取 {name} 数据出错: {e}")
            
    return alert_messages, date_str

# ==========================================
# 4. 发送邮件引擎 
# ==========================================
def send_email(messages, date_str):
    if not messages:
        subject = f"✅ 【平安信】V15 盘石计划今日巡视正常 ({date_str})"
        mail_content = f"盘石计划长官，您好：\n\n今日 ({date_str}) 交易系统后台巡逻完毕。\n\n目前大盘风平浪静，没有标的触发多级别共振。请安心工作，继续【观望持有】。\n\n--------------------\n此邮件由 V15 盘石计划·多维共振系统 自动发出。"
    else:
        subject = f"🚨 【操作提示】V15 盘石计划·共振信号 ({date_str})"
        mail_content = f"盘石计划长官，您好：\n\n今日 ({date_str}) 交易系统后台巡逻完毕，V15双核引擎捕捉到以下极值信号：\n\n"
        mail_content += "\n\n".join(messages)
        mail_content += "\n\n--------------------\n大级别定生死，小级别找买点。此邮件由 V15 盘石计划自动发出，请严格执行系统纪律。"
    
    msg = MIMEText(mail_content, 'plain', 'utf-8')
    msg['From'] = formataddr((str(Header("V15 盘石量化系统", 'utf-8')), SENDER_EMAIL))
    msg['To'] = formataddr((str(Header("基金经理", 'utf-8')), RECEIVER_EMAIL))
    msg['Subject'] = Header(subject, 'utf-8')
    
    try:
        smtpObj = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        smtpObj.login(SENDER_EMAIL, SENDER_PWD)
        smtpObj.sendmail(SENDER_EMAIL, [RECEIVER_EMAIL], msg.as_string())
        smtpObj.quit()
        print(f"邮件发送成功！今日类型：{'平安信' if not messages else '警报信'}")
    except smtplib.SMTPException as e:
        print(f"邮件发送失败: {e}")

if __name__ == "__main__":
    alerts, today_date = check_signals()
    send_email(alerts, today_date)
