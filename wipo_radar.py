import requests
import xml.etree.ElementTree as ET
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
import os
from datetime import datetime

# ==========================================
# 1. 邮箱基础配置 (继续白嫖 GitHub Secrets)
# ==========================================
SENDER_EMAIL = os.environ.get('SENDER_EMAIL')      
SENDER_PWD = os.environ.get('SENDER_PASSWORD')     
RECEIVER_EMAIL = os.environ.get('RECEIVER_EMAIL')  
SMTP_SERVER = "smtp.qq.com"  
SMTP_PORT = 465              

# ==========================================
# 2. 核心靶点与研发黑话配置
# ==========================================
# 你的核心靶点，系统会去检索专利的“标题”和“摘要”
TARGETS = ["ENPP3", "CD3", "Bispecific Antibody"] 

# ==========================================
# 3. WIPO 专利底层数据解析引擎
# ==========================================
def fetch_wipo_patents(target):
    # FP:() 代表检索专利的 Front Page (包含标题和摘要)
    # 按照公布日期倒序排列，只抓取最新的
    rss_url = f"https://patentscope.wipo.int/search/en/rss.jsf?query=FP:({target})&sortOption=Pub+Date+Desc"
    
    # 伪装成浏览器，防止 WIPO 防火墙拦截
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        resp = requests.get(rss_url, headers=headers, timeout=15)
        
        # 解析 XML/RSS 数据
        root = ET.fromstring(resp.content)
        items = []
        
        # 遍历所有专利条目，提取最新的前 3 篇
        for item in root.findall('.//item'):
            title = item.find('title').text if item.find('title') is not None else "无标题"
            link = item.find('link').text if item.find('link') is not None else ""
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else "未知日期"
            
            # WIPO 的标题通常包含专利号和公司名，我们直接提取
            items.append(f"📜 {title}\n   公布时间: {pub_date}\n   专利原文: {link}")
            
            if len(items) >= 3:  # 避免邮件太长，每个靶点只推送最新的 3 篇
                break
                
        return items
    except Exception as e:
        print(f"抓取 {target} 专利失败: {e}")
        return []

# ==========================================
# 4. 邮件组装与发送引擎
# ==========================================
def main():
    date_str = datetime.now().strftime("%Y-%m-%d")
    all_messages = []
    total_patents = 0
    
    for target in TARGETS:
        print(f"正在扫描 WIPO 专利库，目标: {target} ...")
        patents = fetch_wipo_patents(target)
        if patents:
            total_patents += len(patents)
            all_messages.append(f"🛡️ 【{target}】 领域最新截获专利：\n\n" + "\n\n".join(patents))
            
    if total_patents == 0:
        subject = f"✅ 【专利周报】WIPO 专利雷达巡视正常 ({date_str})"
        content = f"长官，您好：\n\n今日 ({date_str}) WIPO 国际专利数据库扫描完毕。\n\n本周您的核心靶点暂无高相关性新专利公布。\n\n--------------------\n此邮件由 AI 专利情报官 自动发出。"
    else:
        subject = f"🚨 【专利预警】WIPO 截获 {total_patents} 篇核心靶点新专利 ({date_str})"
        content = f"长官，您好：\n\n这是本周的 WIPO 专利监控简报，请重点排查是否有竞品的 FTO (自由实施) 冲突：\n\n"
        content += "\n====================\n\n".join(all_messages)
        content += "\n\n--------------------\n及时掌握专利布局，打造坚实护城河。此邮件由 AI 专利情报官 自动发出。"
        
    msg = MIMEText(content, 'plain', 'utf-8')
    msg['From'] = formataddr((str(Header("AI 专利情报官", 'utf-8')), SENDER_EMAIL))
    msg['To'] = formataddr((str(Header("研发科学家", 'utf-8')), RECEIVER_EMAIL))
    msg['Subject'] = Header(subject, 'utf-8')
    
    try:
        smtpObj = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        smtpObj.login(SENDER_EMAIL, SENDER_PWD)
        smtpObj.sendmail(SENDER_EMAIL, [RECEIVER_EMAIL], msg.as_string())
        smtpObj.quit()
        print(f"邮件发送成功！共推送 {total_patents} 篇专利。")
    except smtplib.SMTPException as e:
        print(f"邮件发送失败: {e}")

if __name__ == "__main__":
    main()
