from flask import Flask, render_template_string, request, send_file
import requests
from bs4 import BeautifulSoup
import pandas as pd
import io
import re
import os

app = Flask(__name__)

# --- 공통 스타일 및 레이아웃 ---
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>최대한의 부동산 종합 툴킷</title>
    <style>
        body { font-family: '맑은 고딕'; background-color: #f4f7f6; margin: 0; padding: 0; }
        .nav { background: #1F4E78; padding: 15px; text-align: center; }
        .nav a { color: white; margin: 0 20px; text-decoration: none; font-weight: bold; font-size: 18px; }
        .nav a:hover { color: #ffc107; }
        .container { padding: 50px; text-align: center; }
        .box { background: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); display: inline-block; width: 90%; max-width: 900px; }
        h1 { color: #1F4E78; }
        input { padding: 12px; width: 60%; border: 1px solid #ddd; border-radius: 5px; margin-bottom: 10px; font-size: 16px; }
        button { padding: 12px 25px; background: #1F4E78; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; margin: 5px; }
        .excel-btn { background: #28a745; margin-bottom: 15px; }
        .result-table { width: 100%; border-collapse: collapse; margin-top: 20px; text-align: left; }
        .result-table th, .result-table td { padding: 12px; border-bottom: 1px solid #eee; font-size: 14px; }
        .source-tag { font-size: 11px; padding: 2px 6px; border-radius: 3px; margin-right: 5px; color: white; font-weight: bold; }
        .naver { background: #03cf5d; }
        .google { background: #4285f4; }
        .addr-text { color: #d9534f; font-weight: bold; }
    </style>
</head>
<body>
    <div class="nav">
        <a href="/?mode=price">📊 시세 분석기</a>
        <a href="/?mode=addr">🔍 지주택 주소 추출기</a>
    </div>

    <div class="container">
        <div class="box">
            {% if mode == 'addr' %}
                <h1>🔍 지주택 사업지 주소 추출기</h1>
                <p>전국 지주택 공고 및 뉴스에서 주소와 고유번호를 낚아챕니다.</p>
            {% else %}
                <h1>📊 실시간 시세/뉴스 분석기</h1>
                <p>네이버와 구글의 최신 부동산 동향을 한눈에 파악합니다.</p>
            {% endif %}

            <form method="POST">
                <input type="text" name="keyword" placeholder="키워드 입력" required>
                <br>
                <button type="submit">데이터 수집 시작</button>
            </form>

            {% if results %}
                <form action="/download" method="POST">
                    <input type="hidden" name="data" value="{{ excel_data | join('|||') }}">
                    <input type="hidden" name="mode" value="{{ mode }}">
                    <button type="submit" class="excel-btn">📥 결과 엑셀 다운로드</button>
                </form>
                <table class="result-table">
                    <thead>
                        <tr>
                            <th>출처</th>
                            <th>제목</th>
                            {% if mode == 'addr' %}<th>포착된 주소/번호</th>{% endif %}
                        </tr>
                    </thead>
                    <tbody>
                        {% for res in results %}
                        <tr>
                            <td><span class="source-tag {{ 'naver' if res.source == '네이버' else 'google' }}">{{ res.source }}</span></td>
                            <td><a href="{{ res.link }}" target="_blank">{{ res.title }}</a></td>
                            {% if mode == 'addr' %}<td><span class="addr-text">{{ res.address }}</span></td>{% endif %}
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            {% endif %}
        </div>
    </div>
</body>
</html>
'''

def extract_address(text):
    addr_pattern = r'([가-힣]+[시|도]\s[가-힣]+[구|군|시]\s[가-힣]+[동|읍|면]\s?\d*-?\d*)'
    biz_pattern = r'\d{3}-\d{2}-\d{5}'
    addrs = re.findall(addr_pattern, text)
    biz_ids = re.findall(biz_pattern, text)
    found = addrs + biz_ids
    return ", ".join(found) if found else "수동 확인"

@app.route('/', methods=['GET', 'POST'])
def home():
    mode = request.args.get('mode', 'price') # 기본값은 시세 분석
    results = []
    excel_data = []
    
    if request.method == 'POST':
        keyword = request.form.get('keyword')
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        
        # 1. 네이버 수집
        try:
            n_url = f"https://search.naver.com/search.naver?where=news&query={keyword}"
            n_res = requests.get(n_url, headers=headers, timeout=10)
            n_soup = BeautifulSoup(n_res.text, 'html.parser')
            items = n_soup.select('.news_wrap')
            for item in items[:15]:
                title = item.select_one('.news_tit').get_text()
                link = item.select_one('.news_tit').get('href')
                desc = item.select_one('.news_dsc').get_text() if item.select_one('.news_dsc') else ""
                
                if mode == 'addr':
                    addr = extract_address(title + " " + desc)
                    results.append({'source': '네이버', 'title': title, 'link': link, 'address': addr})
                    excel_data.append(f"네이버|{title}|{addr}|{link}")
                else:
                    results.append({'source': '네이버', 'title': title, 'link': link})
                    excel_data.append(f"네이버|{title}|{link}")
        except: pass

        # 2. 구글 수집
        try:
            g_url = f"https://news.google.com/rss/search?q={keyword}&hl=ko&gl=KR&ceid=KR:ko"
            g_res = requests.get(g_url, headers=headers, timeout=10)
            g_soup = BeautifulSoup(g_res.content, "lxml-xml")
            for item in g_soup.findAll('item')[:10]:
                title = item.find('title').text
                link = item.find('link').text
                if mode == 'addr':
                    addr = extract_address(title)
                    results.append({'source': '구글', 'title': title, 'link': link, 'address': addr})
                    excel_data.append(f"구글|{title}|{addr}|{link}")
                else:
                    results.append({'source': '구글', 'title': title, 'link': link})
                    excel_data.append(f"구글|{title}|{link}")
        except: pass

    return render_template_string(HTML_TEMPLATE, mode=mode, results=results, excel_data=excel_data)

@app.route('/download', methods=['POST'])
def download():
    mode = request.form.get('mode')
    raw_data = request.form.get('data').split('|||')
    parsed_data = [item.split('|') for item in raw_data if '|' in item]
    
    cols = ['출처', '제목', '주소/번호', '링크'] if mode == 'addr' else ['출처', '제목', '링크']
    df = pd.DataFrame(parsed_data, columns=cols)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name=f"{'지주택' if mode=='addr' else '시세'}_데이터.xlsx")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)