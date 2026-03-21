import requests
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
import os
from datetime import datetime

# ==========================================
# 1. 邮箱基础配置 (复用你之前存好的 Secrets)
# ==========================================
SENDER_EMAIL = os.environ.get('SENDER_EMAIL')      
SENDER_PWD = os.environ.get('SENDER_PASSWORD')     
RECEIVER_EMAIL = os.environ.get('RECEIVER_EMAIL')  
SMTP_SERVER = "smtp.qq.com"  # 如果是网易请改为 smtp.163.com
SMTP_PORT = 465              

# ==========================================
# 2. 核心靶点配置
# ==========================================
TARGETS = ["ENPP3", "CD3"]
DAYS_BACK = 2  # 检索过去 48 小时内新收录的文献 (留出余量，防止错过)

# ==========================================
# 3. NCBI PubMed API 检索引擎
# ==========================================
def fetch_pubmed(target, days):
    # 第一步：搜索文献 ID (PMID)
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    search_params = {
        "db": "pubmed",
        "term": f'"{target}"[Title/Abstract]', # 精准匹配标题或摘要中包含靶点的文献
        "retmode": "json",
        "reldate": days,
        "datetype": "edat", # 按文献录入数据库的时间筛选，最适合做每日追踪
        "tool": "github_actions_radar",
        "email": RECEIVER_EMAIL
    }
    
    try:
        res = requests.get(search_url, params=search_params, timeout=10).json()
        id_list = res.get("esearchresult", {}).get("idlist", [])
        
        if not id_list:
            return []
            
        # 第二步：根据 PMID 获取文献详细信息 (标题、期刊、日期)
        summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        summary_params = {
            "db": "pubmed",
            "id": ",".join(id_list),
            "retmode": "json"
        }
        sum_res = requests.get(summary_url, params=summary_params, timeout=10).json()
        
        articles = []
        for pmid in id_list:
            doc = sum_res.get("result", {}).get(pmid, {})
            title = doc.get("title", "No Title")
            journal = doc.get("fulljournalname", "Unknown Journal")
            pubdate = doc.get("pubdate", "Unknown Date")
            link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            articles.append(f"📌 {title}\n   期刊: {journal} ({pubdate})\n   链接: {link}")
            
        return articles
    except Exception as e:
        print(f"抓取 {target} 失败: {e}")
        return []

# ==========================================
# 4. 邮件组装与发送引擎
# ==========================================
def main():
    date_str = datetime.now().strftime("%Y-%m-%d")
    all_messages = []
    total_articles = 0
    
    for target in TARGETS:
        print(f"正在检索靶点: {target} ...")
        articles = fetch_pubmed(target, DAYS_BACK)
        if articles:
            total_articles += len(articles)
            all_messages.append(f"🧬 【{target}】 发现 {len(articles)} 篇最新文献：\n\n" + "\n\n".join(articles))
            
    # 根据结果切换平安信或警报信
    if total_articles == 0:
        subject = f"✅ 【科研平安信】PubMed 雷达今日巡视正常 ({date_str})"
        content = f"长官，您好：\n\n今日 ({date_str}) PubMed 数据库检索完毕。\n\n您关注的核心靶点 ENPP3 和 CD3 在过去 48 小时内暂无新文献收录。请安心推进实验。\n\n--------------------\n此邮件由 AI 科研情报官 自动发出。"
    else:
        subject = f"🚨 【文献速递】PubMed 发现 {total_articles} 篇核心靶点新进展 ({date_str})"
        content = f"长官，您好：\n\n今日 ({date_str}) PubMed 雷达检索到最新文献，请查阅：\n\n"
        content += "\n====================\n\n".join(all_messages)
        content += "\n\n--------------------\n此邮件由 AI 科研情报官 自动发出，助力您的抗体研发工作。"
        
    msg = MIMEText(content, 'plain', 'utf-8')
    msg['From'] = formataddr((str(Header("AI 科研情报官", 'utf-8')), SENDER_EMAIL))
    msg['To'] = formataddr((str(Header("研发科学家", 'utf-8')), RECEIVER_EMAIL))
    msg['Subject'] = Header(subject, 'utf-8')
    
    try:
        smtpObj = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        smtpObj.login(SENDER_EMAIL, SENDER_PWD)
        smtpObj.sendmail(SENDER_EMAIL, [RECEIVER_EMAIL], msg.as_string())
        smtpObj.quit()
        print(f"邮件发送成功！共推送 {total_articles} 篇文献。")
    except smtplib.SMTPException as e:
        print(f"邮件发送失败: {e}")

if __name__ == "__main__":
    main()
