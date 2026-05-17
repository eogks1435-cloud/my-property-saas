from flask import Flask, render_template_string, request, send_file
import requests
from bs4 import BeautifulSoup
import pandas as pd
import io

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>부동산 통합 데이터 추출기</title>
    <style>
        body { font-family: '맑은 고딕'; text-align: center; padding: 50px; background-color: #f4f7f6; }
        .container { background: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); display: inline-block; width: 80%; max-width: 850px; }
        h1 { color: #1F4E78; }
        .source-tag { font-size: 11px; padding: 2px 6px; border-radius: 3px; margin-right: 5px; color: white; font-weight: bold; }
        .naver { background: #03cf5d; }
        .google { background: #4285f4; }
        input { padding: 12px; width: 60%; border: 1px solid #ddd; border-radius: 5px; margin-bottom: 10px; font-size: 16px; }
        button { padding: 12px 25px; background: #1F4E78; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; margin: 5px; }
        .excel-btn { background: #28a745; margin-top: 10px; }
        .result-item { text-align: left; background: #fff; border: 1px solid #eee; margin-bottom: 10px; padding: 15px; border-left: 5px solid #1f4e78; border-radius: 5px; }
        .result-item a { text-decoration: none; color: #333; font-weight: bold; }
        .no-data { color: #d9534f; margin-top: 20px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏗️ 대표님 전용 네이버+구글 통합 분석기</h1>
        <form method="POST">
            <input type="text" name="keyword" placeholder="단지명 입력 (예: 반포자이)" required>
            <br>
            <button type="submit">실시간 데이터 통합 수집</button>
        </form>
        
        {% if results %}
            <form action="/download" method="POST">
                <input type="hidden" name="data" value="{{ excel_data | join('|||') }}">
                <button type="submit" class="excel-btn">📥 통합 결과 엑셀 다운로드</button>
            </form>
            <div style="margin-top:20px;">
                {% for res in results %}
                    <div class="result-item">
                        <span class="source-tag {{ 'naver' if res.source == '네이버' else 'google' }}">{{ res.source }}</span>
                        <a href="{{ res.link }}" target="_blank"> {{ res.title }}</a>
                    </div>
                {% endfor %}
            </div>
        {% elif searched %}
            <p class="no-data">⚠️ 네이버 보안으로 인해 일시적으로 수집이 지연되고 있습니다. 잠시 후 단어를 바꿔 시도해 주세요.</p>
        {% endif %}
    </div>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def home():
    results = []
    excel_data = []
    searched = False
    if request.method == 'POST':
        searched = True
        keyword = request.form.get('keyword')
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.naver.com/'
        }
        
        # 1. 네이버 뉴스 검색 페이지 직접 수집 (RSS 대신 우회)
        try:
            n_url = f"https://search.naver.com/search.naver?where=news&query={keyword}"
            n_res = requests.get(n_url, headers=headers, timeout=10)
            n_soup = BeautifulSoup(n_res.text, 'html.parser')
            # 네이버 뉴스 기사 제목의 공통 클래스 'news_tit'를 노립니다.
            n_items = n_soup.select('.news_tit')
            for item in n_items[:10]:
                title = item.get_text()
                link = item.get('href')
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
                results.append({'source': '구글', 'title': title, 'link': link})
                excel_data.append(f"구글|{title}|{link}")
        except: pass
            
    # 서버 실행 설정 (Render 포트 대응)
    return render_template_string(HTML_TEMPLATE, results=results, excel_data=excel_data, searched=searched)

@app.route('/download', methods=['POST'])
def download():
    raw_data = request.form.get('data').split('|||')
    parsed_data = [item.split('|') for item in raw_data if '|' in item]
    df = pd.DataFrame(parsed_data, columns=['출처', '뉴스 제목', '링크'])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="통합_부동산_데이터.xlsx")

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)