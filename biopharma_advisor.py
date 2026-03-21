import requests
import xml.etree.ElementTree as ET
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
import os
from datetime import datetime

# ==========================================
# 1. 邮箱基础配置 (继续共享之前的密码箱)
# ==========================================
SENDER_EMAIL = os.environ.get('SENDER_EMAIL')      
SENDER_PWD = os.environ.get('SENDER_PASSWORD')     
RECEIVER_EMAIL = os.environ.get('RECEIVER_EMAIL')  
SMTP_SERVER = "smtp.qq.com"  
SMTP_PORT = 465              

# ==========================================
# 2. 顾问情报检索策略 (锁定全球医药重磅新闻)
# 使用 when:1d 确保只抓取过去 24 小时的新闻
# ==========================================
NEWS_CATEGORIES = {
    "💰 资本与交易 (M&A, 授权, 融资)": '("biotech" OR "pharma") AND ("acquisition" OR "buyout" OR "licensing" OR "merger" OR "IPO") when:1d',
    "🚀 临床与监管 (FDA审批, 核心数据读出)": '("FDA" OR "EMA" OR "Phase 3" OR "clinical trial") AND ("approval" OR "breakthrough" OR "fails" OR "meets endpoint") when:1d',
    "🔬 前沿科技与靶点突破 (Science & Tech)": '("bispecific" OR "ADC" OR "TCE" OR "mRNA" OR "gene editing") AND ("breakthrough" OR "novel" OR "discovery") when:1d'
}

# ==========================================
# 3. Google News 全球医药聚合引擎
# ==========================================
def fetch_global_news(query_string):
    # 调用 Google News 英文原版 RSS (全球最全的医药商业新闻源)
    url = "https://news.google.com/rss/search"
    params = {
        "q": query_string,
        "hl": "en-US",
        "gl": "US",
        "ceid": "US:en"
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        root = ET.fromstring(resp.content)
        
        articles = []
        # 遍历新闻条目，每个板块最多只提取最核心的前 5 条，避免信息过载
        for item in root.findall('.//item')[:5]:
            title = item.find('title').text if item.find('title') is not None else "No Title"
            link = item.find('link').text if item.find('link') is not None else ""
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else "Unknown Date"
            
            # 清洗一下来源名称 (通常在标题的最后)
            clean_title = title.split(' - ')[0] if ' - ' in title else title
            source = title.split(' - ')[-1] if ' - ' in title else "Web"
            
            articles.append(f"📰 {clean_title}\n   来源: {source} ({pub_date})\n   直达: {link}")
            
        return articles
    except Exception as e:
        print(f"抓取新闻失败: {e}")
        return []

# ==========================================
# 4. 邮件组装与发送引擎
# ==========================================
def main():
    date_str = datetime.now().strftime("%Y-%m-%d")
    all_messages = []
    total_news = 0
    
    for category_name, query_string in NEWS_CATEGORIES.items():
        print(f"正在扫描板块: {category_name} ...")
        news_items = fetch_global_news(query_string)
        if news_items:
            total_news += len(news_items)
            all_messages.append(f"【{category_name}】\n\n" + "\n\n".join(news_items))
            
    if total_news == 0:
        subject = f"☕ 【早安】全球生物医药商业雷达今日平静 ({date_str})"
        content = f"长官，早上好：\n\n今日 ({date_str}) 医药情报网络巡视完毕。过去 24 小时内全球暂无重磅的 M&A 或 FDA 突发新闻。\n\n祝您今天实验顺利，投资长虹！\n\n--------------------\n此邮件由 AI 医药投资顾问 自动发出。"
    else:
        subject = f"🌍 【医药晨报】今日全球重磅交易与临床进展汇编 ({date_str})"
        content = f"长官，早上好：\n\n边喝咖啡边阅览天下事。以下是过去 24 小时内全球生物医药圈的最核心动态：\n\n"
        content += "\n====================\n\n".join(all_messages)
        content += "\n\n--------------------\n洞察商业流向，预判科技未来。此邮件由 AI 医药投资顾问 自动发出。"
        
    msg = MIMEText(content, 'plain', 'utf-8')
    msg['From'] = formataddr((str(Header("AI 医药投资顾问", 'utf-8')), SENDER_EMAIL))
    msg['To'] = formataddr((str(Header("研发与投资官", 'utf-8')), RECEIVER_EMAIL))
    msg['Subject'] = Header(subject, 'utf-8')
    
    try:
        smtpObj = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        smtpObj.login(SENDER_EMAIL, SENDER_PWD)
        smtpObj.sendmail(SENDER_EMAIL, [RECEIVER_EMAIL], msg.as_string())
        smtpObj.quit()
        print(f"邮件发送成功！共推送 {total_news} 条重磅新闻。")
    except smtplib.SMTPException as e:
        print(f"邮件发送失败: {e}")

if __name__ == "__main__":
    main()
