from flask import Flask, render_template_string, request, send_file
import requests
import pandas as pd
import io
import os

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>전국 지주택 주소 추출기</title>
    <style>
        body { font-family: '맑은 고딕'; background-color: #f4f7f6; text-align: center; padding: 50px; }
        .box { background: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); display: inline-block; width: 90%; max-width: 900px; }
        h1 { color: #1F4E78; }
        input { padding: 12px; width: 60%; border: 1px solid #ddd; border-radius: 5px; font-size: 16px; }
        button { padding: 12px 25px; background: #1F4E78; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; text-align: left; }
        th, td { padding: 12px; border-bottom: 1px solid #eee; font-size: 14px; }
        .addr { color: #d9534f; font-weight: bold; }
    </style>
</head>
<body>
    <div class="box">
        <h1>📍 전국 지주택 주소 자동 리스트</h1>
        <p>네이버 지도 데이터를 기반으로 실제 사업지/사무실 주소를 추출합니다.</p>
        <form method="POST">
            <input type="text" name="keyword" placeholder="예: 서울 지역주택조합" required>
            <button type="submit">리스트 추출</button>
        </form>
        {% if results %}
            <form action="/download" method="POST">
                <input type="hidden" name="data" value="{{ excel_data | join('|||') }}">
                <button type="submit" style="background:#28a745; margin: 10px 0;">📥 엑셀로 저장하기</button>
            </form>
            <table>
                <thead>
                    <tr>
                        <th>조합/사무실 명칭</th>
                        <th>정확한 주소</th>
                        <th>전화번호</th>
                    </tr>
                </thead>
                <tbody>
                    {% for res in results %}
                    <tr>
                        <td>{{ res.name }}</td>
                        <td class="addr">{{ res.address }}</td>
                        <td>{{ res.tel }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        {% endif %}
    </div>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def home():
    results, excel_data = [], []
    if request.method == 'POST':
        keyword = request.form.get('keyword')
        # 네이버 지도의 검색 API 통로를 사용합니다 (사람인 척 가장)
        url = f"https://map.naver.com/v5/api/search?caller=pcweb&query={keyword}&type=all&searchCoord=127.001|37.564&page=1&displayCount=20"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://map.naver.com/'
        }
        
        try:
            res = requests.get(url, headers=headers)
            data = res.json()
            items = data['result']['place']['list']
            
            for item in items:
                name = item['name']
                address = item['address']
                tel = item['tel'] if item.get('tel') else "번호 없음"
                results.append({'name': name, 'address': address, 'tel': tel})
                excel_data.append(f"{name}|{address}|{tel}")
        except Exception as e:
            print(f"Error: {e}")
            
    return render_template_string(HTML_TEMPLATE, results=results, excel_data=excel_data)

@app.route('/download', methods=['POST'])
def download():
    raw_data = request.form.get('data').split('|||')
    parsed_data = [item.split('|') for item in raw_data if '|' in item]
    df = pd.DataFrame(parsed_data, columns=['명칭', '주소', '전화번호'])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="지주택_리스트.xlsx")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)