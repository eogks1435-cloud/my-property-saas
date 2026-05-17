from flask import Flask, render_template_string, request, send_file
import requests
from bs4 import BeautifulSoup
import pandas as pd
import io
import os
import re

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>전국 지주택 주소 추출기 (Google 우회)</title>
    <style>
        body { font-family: '맑은 고딕'; background-color: #f4f7f6; text-align: center; padding: 50px; }
        .box { background: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); display: inline-block; width: 95%; max-width: 1000px; }
        h1 { color: #1F4E78; }
        input { padding: 12px; width: 60%; border: 1px solid #ddd; border-radius: 5px; font-size: 16px; }
        button { padding: 12px 25px; background: #1F4E78; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; text-align: left; }
        th, td { padding: 12px; border-bottom: 1px solid #eee; font-size: 14px; }
        .addr { color: #d9534f; font-weight: bold; background: #fff0f0; }
    </style>
</head>
<body>
    <div class="box">
        <h1>📍 전국 지주택 주소 자동 리스트 (Google 기반)</h1>
        <p>네이버 차단을 피해 구글의 방대한 데이터를 바탕으로 주소를 추출합니다.</p>
        <form method="POST">
            <input type="text" name="keyword" placeholder="예: 경기도 지역주택조합 현황 주소" required>
            <button type="submit">데이터 추출</button>
        </form>
        {% if results %}
            <form action="/download" method="POST">
                <input type="hidden" name="data" value="{{ excel_data | join('|||') }}">
                <button type="submit" style="background:#28a745; margin: 10px 0;">📥 엑셀로 저장하기</button>
            </form>
            <table>
                <thead>
                    <tr>
                        <th>명칭</th>
                        <th>추출된 주소 패턴</th>
                        <th>출처 링크</th>
                    </tr>
                </thead>
                <tbody>
                    {% for res in results %}
                    <tr>
                        <td>{{ res.name }}</td>
                        <td class="addr">{{ res.address }}</td>
                        <td><a href="{{ res.link }}" target="_blank">기사/공고 확인</a></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        {% endif %}
    </div>
</body>
</html>
'''

def extract_addr(text):
    # 구글 검색 결과 요약문에서 주소 패턴만 쏙 뽑아내는 필터입니다.
    pattern = r'([가-힣]+[시|도]\s[가-힣]+[구|군|시]\s[가-힣]+[동|읍|면|로]\s?\d*-?\d*)'
    found = re.findall(pattern, text)
    return ", ".join(list(set(found))) if found else "상세페이지 확인"

@app.route('/', methods=['GET', 'POST'])
def home():
    results, excel_data = [], []
    if request.method == 'POST':
        keyword = request.form.get('keyword')
        # 구글은 RSS가 아닌 일반 검색결과를 더 깊게 뒤집니다.
        search_url = f"https://www.google.com/search?q={keyword}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'}
        
        try:
            res = requests.get(search_url, headers=headers)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # 구글 검색 결과의 각 항목들을 뒤집니다.
            for g in soup.select('.tF2Cxc'):
                title = g.select_one('.DKV0Md').text if g.select_one('.DKV0Md') else "정보 없음"
                link = g.select_one('.yuRUbf a')['href'] if g.select_one('.yuRUbf a') else "#"
                snippet = g.select_one('.VwiC3b').text if g.select_one('.VwiC3b') else ""
                
                addr = extract_addr(title + " " + snippet)
                results.append({'name': title, 'address': addr, 'link': link})
                excel_data.append(f"{title}|{addr}|{link}")
        except Exception as e:
            print(e)
            
    return render_template_string(HTML_TEMPLATE, results=results, excel_data=excel_data)

@app.route('/download', methods=['POST'])
def download():
    raw_data = request.form.get('data').split('|||')
    parsed_data = [item.split('|') for item in raw_data if '|' in item]
    df = pd.DataFrame(parsed_data, columns=['명칭', '주소', '링크'])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="지주택_추출리스트.xlsx")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)