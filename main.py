import os
import requests
from dotenv import load_dotenv
from flask import Flask, abort, render_template_string

# --- 應用程式設定 (不變) ---
load_dotenv()
app = Flask(__name__)

APS_CLIENT_ID = os.environ.get('APS_CLIENT_ID')
APS_CLIENT_SECRET = os.environ.get('APS_CLIENT_SECRET')
APS_AUTH_URL = 'https://developer.api.autodesk.com/authentication/v2/token'

if not all([APS_CLIENT_ID, APS_CLIENT_SECRET]):
    raise SystemExit("錯誤：請先在 .env 檔案中設定您的 APS_CLIENT_ID 和 APS_CLIENT_SECRET")

# --- 輔助函式 (不變) ---
def get_aps_token():
    try:
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = { 'grant_type': 'client_credentials', 'client_id': APS_CLIENT_ID, 'client_secret': APS_CLIENT_SECRET, 'scope': 'viewables:read data:read' }
        response = requests.post(APS_AUTH_URL, headers=headers, data=data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"獲取 Token 時發生錯誤: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"API 回應內容: {e.response.text}")
        return None

# --- HTML 樣板 ---

# 專為 3D 設計的 HTML + JS
HTML_TEMPLATE_3D = """
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>Autodesk 3D Viewer</title><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="stylesheet" href="https://developer.api.autodesk.com/modelderivative/v2/viewers/7.*/style.min.css" type="text/css"><style>body, html {{ margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; }} #viewerContainer {{ width: 100%; height: 100%; }}</style></head><body><div id="viewerContainer"></div><script src="https://developer.api.autodesk.com/modelderivative/v2/viewers/7.*/viewer3D.min.js"></script>
<script>
    const ACCESS_TOKEN = '{access_token}';
    const MODEL_URN = '{model_urn}';
    let viewer;

    function onDocumentLoadSuccess(doc) {{
        const viewables = doc.getRoot().search({{ 'type': 'geometry', 'role': '3d' }});
        if (viewables.length === 0) {{
            alert("錯誤：在此 URN 中找不到 3D 視圖。");
            return;
        }}
        viewer.loadDocumentNode(doc, viewables[0]);
    }}

    function onDocumentLoadFailure(errorCode) {{ console.error('載入模型失敗 - ' + errorCode); }}

    Autodesk.Viewing.Initializer({{ env: 'AutodeskProduction', accessToken: ACCESS_TOKEN }}, () => {{
        viewer = new Autodesk.Viewing.GuiViewer3D(document.getElementById('viewerContainer'));
        viewer.start();
        // 預設 3D 的深色主題
        viewer.setTheme('dark-theme');
        viewer.setLightPreset(2); // "Dark Sky" 環境
        viewer.setEnvMapBackground(true);
        Autodesk.Viewing.Document.load('urn:' + MODEL_URN, onDocumentLoadSuccess, onDocumentLoadFailure);
    }});
</script></body></html>
"""

# 專為 2D 設計的 HTML + JS
HTML_TEMPLATE_2D = """
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>Autodesk 2D Viewer</title><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="stylesheet" href="https://developer.api.autodesk.com/modelderivative/v2/viewers/7.*/style.min.css" type="text/css"><style>body, html {{ margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; }} #viewerContainer {{ width: 100%; height: 100%; }}</style></head><body><div id="viewerContainer"></div><script src="https://developer.api.autodesk.com/modelderivative/v2/viewers/7.*/viewer3D.min.js"></script>
<script>
    const ACCESS_TOKEN = '{access_token}';
    const MODEL_URN = '{model_urn}';
    let viewer;

    function onDocumentLoadSuccess(doc) {{
        const viewables = doc.getRoot().search({{ 'type': 'geometry', 'role': '2d' }});
        if (viewables.length === 0) {{
            alert("錯誤：在此 URN 中找不到 2D 視圖。");
            return;
        }}
        viewer.loadDocumentNode(doc, viewables[0]);
    }}

    function onDocumentLoadFailure(errorCode) {{ console.error('載入模型失敗 - ' + errorCode); }}

    Autodesk.Viewing.Initializer({{ env: 'AutodeskProduction', accessToken: ACCESS_TOKEN }}, () => {{
        viewer = new Autodesk.Viewing.GuiViewer3D(document.getElementById('viewerContainer'));
        viewer.start();
        // 預設 2D 的深色主題
        // 這個設定等同於您在截圖中點擊的那個按鈕，會將圖紙顏色反轉（黑底白線）
        viewer.prefs.set('swapBlackAndWhite', true);
        Autodesk.Viewing.Document.load('urn:' + MODEL_URN, onDocumentLoadSuccess, onDocumentLoadFailure);
    }});
</script></body></html>
"""

# --- Flask 路由 ---
@app.route('/')
def index():
    return """
    <h1>動態 URN 檢視器</h1>
    <p>檢視 3D 模型請用: /view3d/&lt;您的URN&gt;</p>
    <p>檢視 2D 圖紙請用: /view2d/&lt;您的URN&gt;</p>
    """

@app.route('/view3d/<string:urn>')
def show_3d_viewer(urn):
    """專門處理 3D 模型的路由"""
    token_data = get_aps_token()
    if not token_data:
        abort(500, description="無法取得認證 Token。")
    
    html_content = HTML_TEMPLATE_3D.format(
        access_token=token_data['access_token'],
        model_urn=urn
    )
    return html_content

@app.route('/view2d/<string:urn>')
def show_2d_viewer(urn):
    """專門處理 2D 圖紙的路由"""
    token_data = get_aps_token()
    if not token_data:
        abort(500, description="無法取得認證 Token。")

    html_content = HTML_TEMPLATE_2D.format(
        access_token=token_data['access_token'],
        model_urn=urn
    )
    return html_content

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)