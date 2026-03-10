import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# 目标高管职级关键词
EXECUTIVE_KEYWORDS = ["director", "vice president", "vp", "chief", "head"]

def is_executive(title):
    title_lower = title.lower()
    return any(keyword in title_lower for keyword in EXECUTIVE_KEYWORDS)

def extract_level(title):
    title_lower = title.lower()
    if "vice president" in title_lower or "vp" in title_lower:
        return "Vice President"
    elif "executive director" in title_lower:
        return "Executive Director"
    elif "senior director" in title_lower:
        return "Senior Director"
    elif "director" in title_lower:
        return "Director"
    return "Executive"

def scrape_biontech():
    print("开始抓取 BioNTech 官网...")
    jobs = []
    url = "[https://jobs.biontech.com/go/All-Jobs/8781301/?locale=en_US&previewCategory=true&referrerSave=false](https://jobs.biontech.com/go/All-Jobs/8781301/?locale=en_US&previewCategory=true&referrerSave=false)"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    try:
        # 直接拉取底层网页数据，避免由于浏览器渲染过慢导致的超时
        response = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(response.text, "html.parser")
        
        job_rows = soup.find_all("tr", class_="data-row")
        print(f"成功获取到网页，找到 {len(job_rows)} 个基础职位。正在过滤高管岗...")
        
        for row in job_rows:
            try:
                # 提取标题
                title_elem = row.find(class_="jobTitle")
                if not title_elem: continue
                title_a = title_elem.find("a")
                title = title_a.text.strip() if title_a else title_elem.text.strip()
                
                # 过滤高管
                if not is_executive(title):
                    continue
                    
                # 提取链接
                if title_a and title_a.has_attr("href"):
                    job_url = title_a["href"]
                    if job_url.startswith("/"):
                        job_url = "[https://jobs.biontech.com](https://jobs.biontech.com)" + job_url
                else:
                    job_url = url
                    
                # 提取地点 (去除多余的换行和空格)
                loc_elem = row.find(class_="jobLocation")
                location = " ".join(loc_elem.text.split()) if loc_elem else "Unknown"
                
                # 提取部门
                dept_elem = row.find(class_="jobFacility")
                department = " ".join(dept_elem.text.split()) if dept_elem else "BioNTech"
                
                # 提取日期
                date_elem = row.find(class_="jobDate")
                date_str = " ".join(date_elem.text.split()) if date_elem else datetime.now().strftime("%Y-%m-%d")

                # 获取 JD 详情
                description = "暂无详细描述"
                if job_url != url:
                    try:
                        jd_res = requests.get(job_url, headers=headers, timeout=10)
                        jd_soup = BeautifulSoup(jd_res.text, "html.parser")
                        jd_span = jd_soup.find("span", class_="jobdescription")
                        if jd_span:
                            full_jd = jd_span.get_text(separator=" ", strip=True)
                            description = full_jd[:300] + "..." if len(full_jd) > 300 else full_jd
                    except Exception as e:
                        print(f"抓取 {title} JD 失败: {e}")

                jobs.append({
                    "title": title,
                    "level": extract_level(title),
                    "department": department,
                    "location": location,
                    "date": date_str,
                    "status": "Active",
                    "sources": ["BioNTech"],
                    "description": description,
                    "url": job_url
                })
            except Exception as e:
                continue
                
    except Exception as e:
        print(f"BioNTech 抓取网络报错: {e}")
            
    print(f"BioNTech 官网抓取完成，筛选出 {len(jobs)} 个高管职位。")
    return jobs

def scrape_linkedin():
    print("开始抓取 LinkedIn 公开接口...")
    jobs = []
    url = "[https://www.linkedin.com/jobs/search/?keywords=BioNTech%20Director&location=Worldwide&f_TPR=r2592000](https://www.linkedin.com/jobs/search/?keywords=BioNTech%20Director&location=Worldwide&f_TPR=r2592000)"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 429:
            print("警告：LinkedIn 拒绝了请求 (429 Too Many Requests)，GitHub IP 可能被暂时封禁。")
            return jobs
            
        soup = BeautifulSoup(response.text, "html.parser")
        job_cards = soup.find_all("div", class_="base-card")
        
        for card in job_cards:
            try:
                title_elem = card.find("h3", class_="base-search-card__title")
                title = title_elem.text.strip() if title_elem else ""
                
                if not is_executive(title):
                    continue
                    
                loc_elem = card.find("span", class_="job-search-card__location")
                location = loc_elem.text.strip() if loc_elem else "Unknown"
                
                url_elem = card.find("a", class_="base-card__full-link")
                job_url = url_elem["href"].split("?")[0] if url_elem else url

                jobs.append({
                    "title": title,
                    "level": extract_level(title),
                    "department": "LinkedIn Sourced",
                    "location": location,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "status": "Active",
                    "sources": ["LinkedIn"],
                    "description": "LinkedIn sourced job. Click link for details.",
                    "url": job_url
                })
            except Exception as e:
                continue
    except Exception as e:
         print(f"LinkedIn 抓取受限或报错: {e}")
         
    print(f"LinkedIn 抓取完成，找到 {len(jobs)} 个高管职位。")
    return jobs

def merge_and_save(biontech_jobs, linkedin_jobs):
    print("开始合并与去重数据...")
    all_jobs = biontech_jobs + linkedin_jobs
    unique_jobs = {}
    
    for job in all_jobs:
        unique_key = f"{job['title'].lower()}|{job['location'].lower()}"
        if unique_key in unique_jobs:
            existing_sources = unique_jobs[unique_key]["sources"]
            new_sources = job["sources"]
            unique_jobs[unique_key]["sources"] = list(set(existing_sources + new_sources))
            
            # 如果是合并数据，优先使用官网的 JD 和链接
            if "BioNTech" in new_sources and "BioNTech" not in existing_sources:
                unique_jobs[unique_key]["url"] = job["url"]
                unique_jobs[unique_key]["description"] = job["description"]
        else:
            job["id"] = len(unique_jobs) + 1
            unique_jobs[unique_key] = job
            
    final_list = list(unique_jobs.values())
    
    # 防空保护机制
    if not final_list:
        print("未抓取到任何有效数据，插入一条诊断测试数据...")
        final_list = [{
            "id": 999,
            "title": "抓取失败诊断提示 (Scraper Blocked/No Data)",
            "level": "Director",
            "department": "System Debug",
            "location": "GitHub Actions",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "status": "Closed",
            "sources": ["System"],
            "description": "如果看到这条提示，说明 GitHub 的 IP 当前暂时无法连接到招聘网站的底层数据。建议查看 GitHub Actions 日志排查。",
            "url": "[https://jobs.biontech.com/go/All-Jobs/8781301/](https://jobs.biontech.com/go/All-Jobs/8781301/)"
        }]
    
    import os
    os.makedirs('public', exist_ok=True)
    
    with open('public/jobs_data.json', 'w', encoding='utf-8') as f:
        json.dump(final_list, f, ensure_ascii=False, indent=2)
        
    print(f"更新成功！最终共计 {len(final_list)} 个职位写入 jobs_data.json。")

if __name__ == "__main__":
    b_jobs = scrape_biontech()
    l_jobs = scrape_linkedin()
    merge_and_save(b_jobs, l_jobs)
