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
    <title>부동산 데이터 추출기</title>
    <style>
        body { font-family: '맑은 고딕'; text-align: center; padding: 50px; background-color: #f4f7f6; }
        .container { background: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); display: inline-block; width: 80%; max-width: 750px; }
        h1 { color: #1F4E78; }
        input { padding: 12px; width: 60%; border: 1px solid #ddd; border-radius: 5px; margin-bottom: 10px; font-size: 16px; }
        button { padding: 12px 25px; background: #1F4E78; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; margin: 5px; }
        .excel-btn { background: #28a745; }
        .result-item { text-align: left; background: #fff; border: 1px solid #eee; margin-bottom: 10px; padding: 15px; border-left: 5px solid #1f4e78; border-radius: 5px; }
        .result-item a { text-decoration: none; color: #333; font-weight: bold; display: block; }
        .result-item a:hover { color: #1F4E78; text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 부동산 데이터 추출기</h1>
        <form method="POST">
            <input type="text" name="keyword" placeholder="키워드 입력 (예: 반포자이)" required>
            <br>
            <button type="submit">데이터 수집</button>
        </form>
        
        {% if results %}
            <form action="/download" method="POST">
                {# 엑셀 저장을 위해 제목들만 따로 보냅니다 #}
                <input type="hidden" name="data" value="{{ titles_only | join('|||') }}">
                <button type="submit" class="excel-btn">📥 결과 엑셀로 받기</button>
            </form>
            <div style="margin-top:20px;">
                {% for res in results %}
                    <div class="result-item">
                        <a href="{{ res.link }}" target="_blank">🔗 {{ res.title }}</a>
                    </div>
                {% endfor %}
            </div>
        {% endif %}
    </div>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def home():
    results = []
    titles_only = []
    if request.method == 'POST':
        keyword = request.form.get('keyword')
        url = f"https://news.google.com/rss/search?q={keyword}&hl=ko&gl=KR&ceid=KR:ko"
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.content, "lxml-xml")
            items = soup.findAll('item') # title 대신 item 전체를 가져옵니다.
            
            for item in items[:15]:
                title = item.find('title').text
                link = item.find('link').text
                results.append({'title': title, 'link': link})
                titles_only.append(title)
        except:
            results = [{"title": "데이터 수집 중 오류가 발생했습니다.", "link": "#"}]
    return render_template_string(HTML_TEMPLATE, results=results, titles_only=titles_only)

@app.route('/download', methods=['POST'])
def download():
    raw_data = request.form.get('data').split('|||')
    df = pd.DataFrame(raw_data, columns=['수집된 부동산 뉴스 제목'])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="부동산_데이터.xlsx")

if __name__ == '__main__':
    app.run(debug=True)