import yfinance as yf
import pandas as pd
import ta
import smtplib
from email.mime.text import MIMEText
from email.header import Header
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
    "紫金矿业": {"code": "601899.SS", "strategy": "死拿"}
}

# ==========================================
# 3. 核心计算引擎
# ==========================================
def check_signals():
    alert_messages = []
    date_str = datetime.now().strftime("%Y-%m-%d") # 默认取今天日期
    
    for name, info in panshi_pool.items():
        if info['strategy'] == "死拿":
            continue 
            
        try:
            df = yf.Ticker(info['code']).history(period="6mo")
            if df.empty: continue
            
            close_s = df['Close'].squeeze()
            df['SMA_20'] = ta.trend.sma_indicator(close_s, window=20)
            df['SMA_60'] = ta.trend.sma_indicator(close_s, window=60)
            df['MACD'] = ta.trend.macd(close_s)
            df['MACD_Signal'] = ta.trend.macd_signal(close_s)
            
            latest = df.iloc[-1] 
            # 动态获取数据最后一天日期（防止周末测试时日期对不上）
            date_str = df.index[-1].strftime("%Y-%m-%d")
            close_price = latest['Close']
            
            signal = "⚪ 观望持有"
            if close_price > latest['SMA_60'] and close_price > latest['SMA_20'] and latest['MACD'] > latest['MACD_Signal']:
                signal = "🟢 触发【买入/加仓】信号 (突破60日线且动能向上)"
            elif close_price < latest['SMA_20']:
                signal = "🔴 触发【卖出/止损】信号 (跌破20日防守线)"
                
            if "🟢" in signal or "🔴" in signal:
                msg = f"【{name}】 最新收盘价: {close_price:.2f}\n   指令: {signal}"
                alert_messages.append(msg)
                
        except Exception as e:
            print(f"获取 {name} 数据出错: {e}")
            
    return alert_messages, date_str

# ==========================================
# 4. 发送邮件引擎 (新增心跳平安信逻辑)
# ==========================================
def send_email(messages, date_str):
    # 根据是否有信号，自动切换邮件的主题和正文
    if not messages:
        subject = f"✅ 【平安信】盘石计划今日巡视正常 ({date_str})"
        mail_content = f"盘石计划长官，您好：\n\n今日 ({date_str}) 交易系统后台巡逻完毕。\n\n目前大盘风平浪静，您的进攻型标的均未触发极值交易信号。请安心工作，继续【观望持有】。\n\n--------------------\n此邮件由 V14 盘石计划·烽火台系统 自动发出。"
    else:
        subject = f"🚨 【操作提示】盘石计划今日交易信号 ({date_str})"
        mail_content = f"盘石计划长官，您好：\n\n今日 ({date_str}) 交易系统后台巡逻完毕，发现以下标的触发极值信号，请查阅：\n\n"
        mail_content += "\n\n".join(messages)
        mail_content += "\n\n--------------------\n此邮件由 V14 盘石计划·烽火台系统 自动发出，请结合宏观面判断是否执行。"
    
    msg = MIMEText(mail_content, 'plain', 'utf-8')
    msg['From'] = Header("V14 盘石量化系统", 'utf-8')
    msg['To'] = Header("基金经理", 'utf-8')
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
