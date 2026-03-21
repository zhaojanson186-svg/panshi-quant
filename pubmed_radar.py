import requests
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
# 2. 混合型检索策略 (核心靶点 + 顶级期刊行业动态)
# ==========================================
SEARCH_QUERIES = {
    # 专属靶点区 (适度放宽，不错过任何线索)
    "专属靶点_ENPP3": '("ENPP3"[tiab] OR "CD203c"[tiab])', # 加入了ENPP3的常用别名
    "专属靶点_CD3_双抗": '("CD3"[tiab]) AND ("Bispecific"[tiab] OR "T-cell engager"[tiab] OR "TCE"[tiab])',
    
    # 行业前沿区 (只看顶级期刊，大浪淘沙)
    "行业动态_CNS顶级突破": '("Nature"[Journal] OR "Science"[Journal] OR "Cell"[Journal] OR "Nature medicine"[Journal] OR "Nature biotechnology"[Journal]) AND ("Antibody"[tiab] OR "Bispecific"[tiab] OR "ADC"[tiab] OR "Autoimmune"[tiab])'
}

DAYS_BACK = 3  # 检索过去 72 小时

# ==========================================
# 3. NCBI PubMed API 检索引擎
# ==========================================
def fetch_pubmed(strategy_name, query_string, days):
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    search_params = {
        "db": "pubmed",
        "term": query_string,  
        "retmode": "json",
        "reldate": days,
        "datetype": "edat", 
        "tool": "github_actions_radar",
        "email": RECEIVER_EMAIL
    }
    
    try:
        res = requests.get(search_url, params=search_params, timeout=10).json()
        id_list = res.get("esearchresult", {}).get("idlist", [])
        
        if not id_list:
            return []
            
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
        print(f"执行策略 [{strategy_name}] 时失败: {e}")
        return []

# ==========================================
# 4. 邮件组装与发送引擎
# ==========================================
def main():
    date_str = datetime.now().strftime("%Y-%m-%d")
    all_messages = []
    total_articles = 0
    
    for strategy_name, query_string in SEARCH_QUERIES.items():
        print(f"正在执行检索策略: {strategy_name} ...")
        articles = fetch_pubmed(strategy_name, query_string, DAYS_BACK)
        if articles:
            total_articles += len(articles)
            all_messages.append(f"🧬 【{strategy_name}】 截获 {len(articles)} 篇文献：\n\n" + "\n\n".join(articles))
            
    if total_articles == 0:
        subject = f"✅ 【科研平安信】PubMed 狙击雷达今日无新文献 ({date_str})"
        content = f"长官，您好：\n\n今日 ({date_str}) PubMed 数据库检索完毕。\n\n您的专属靶点及 CNS 顶级期刊在过去 72 小时内暂无抗体/自免相关的新文献收录。\n\n--------------------\n此邮件由 AI 科研情报官 自动发出。"
    else:
        subject = f"🚨 【文献速递】截获 {total_articles} 篇靶点与行业前沿文献 ({date_str})"
        content = f"长官，您好：\n\n今日 ({date_str}) PubMed 雷达扫描完毕。以下是您的核心靶点进展与全球顶级期刊的最新抗体研发动态：\n\n"
        content += "\n====================\n\n".join(all_messages)
        content += "\n\n--------------------\n保持广阔视野，方能精准狙击。此邮件由 AI 科研情报官 自动发出。"
        
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
