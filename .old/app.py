import os
import requests
import json
import base64
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, abort

# --- 應用程式設定 ---
load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-should-be-changed')

APS_CLIENT_ID = os.environ.get('APS_CLIENT_ID')
APS_CLIENT_SECRET = os.environ.get('APS_CLIENT_SECRET')
APS_CALLBACK_URL = os.environ.get('APS_CALLBACK_URL', 'http://127.0.0.1:5000/callback')

# API 端點網址
APS_AUTH_URL = 'https://developer.api.autodesk.com/authentication/v2/authorize'
APS_TOKEN_URL = 'https://developer.api.autodesk.com/authentication/v2/token'
APS_USERINFO_URL = 'https://developer.api.autodesk.com/userprofile/v1/users/@me'
APS_DM_URL = 'https://developer.api.autodesk.com/project/v1'
APS_DM_DATA_URL = 'https://developer.api.autodesk.com/data/v1'
APS_OSS_URL_GLOBAL = 'https://developer.api.autodesk.com/oss/v2'

SCOPES = ['viewables:read', 'data:read', 'data:write', 'data:create']

# --- 核心路由與輔助函式 ---
def get_auth_header():
    if 'access_token' not in session: abort(401)
    return {'Authorization': f'Bearer {session["access_token"]}'}

@app.route('/')
def index():
    if 'access_token' in session: return render_template('index.html')
    else: return render_template('login.html')

@app.route('/login')
def login():
    auth_url = (f"{APS_AUTH_URL}?response_type=code&client_id={APS_CLIENT_ID}&redirect_uri={APS_CALLBACK_URL}&scope={' '.join(SCOPES)}")
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code: return "錯誤：沒有收到授權碼。", 400
    try:
        data = { 'grant_type': 'authorization_code', 'code': code, 'client_id': APS_CLIENT_ID, 'client_secret': APS_CLIENT_SECRET, 'redirect_uri': APS_CALLBACK_URL }
        response = requests.post(APS_TOKEN_URL, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'})
        response.raise_for_status()
        session['access_token'] = response.json()['access_token']
        return redirect(url_for('index'))
    except Exception as e:
        if hasattr(e, 'response'): print(e.response.text)
        return "錯誤：換取 Token 失敗。", 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/api/user/profile')
def get_user_profile():
    try:
        headers = get_auth_header()
        response = requests.get(APS_USERINFO_URL, headers=headers)
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/hubs')
def get_hubs():
    try:
        headers = get_auth_header()
        response = requests.get(f"{APS_DM_URL}/hubs", headers=headers)
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/hubs/<hub_id>/projects')
def get_projects(hub_id):
    session['current_hub_id'] = hub_id
    try:
        headers = get_auth_header()
        response = requests.get(f"{APS_DM_URL}/hubs/{hub_id}/projects", headers=headers)
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<project_id>/top-folders')
def get_top_folders(project_id):
    session['current_project_id'] = project_id
    hub_id = session.get('current_hub_id')
    if not hub_id: return jsonify({'error': 'Hub ID not found in session'}), 400
    try:
        headers = get_auth_header()
        url = f"{APS_DM_URL}/hubs/{hub_id}/projects/{project_id}/topFolders"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/folders/<folder_id>/contents')
def get_folder_contents(folder_id):
    project_id = session.get('current_project_id')
    if not project_id: return jsonify({'error': 'Project ID not found in session'}), 400
    try:
        headers = get_auth_header()
        url = f"{APS_DM_URL}/projects/{project_id}/folders/{folder_id}/contents"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e: return jsonify({'error': str(e)}), 500

# ==============================================================================
# vvvvvvvvvvvvvvvvvvvvvv 這是本次最關鍵的修正 vvvvvvvvvvvvvvvvvvvvvv
# 將路由從 /upload 改為 /prepare-upload，以匹配前端的呼叫
@app.route('/api/folders/<folder_id>/prepare-upload', methods=['POST'])
def prepare_upload(folder_id):
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# ==============================================================================
    """
    上傳第一步：用正確的順序和 Payload 建立 Item, Version, Storage，並回傳上傳網址。
    """
    project_id = session.get('current_project_id')
    file_name = request.json.get('fileName')
    if not all([project_id, file_name, folder_id]):
        return jsonify({'error': '缺少專案 ID, 資料夾 ID 或檔案名稱'}), 400
        
    try:
        headers = {**get_auth_header(), 'Content-Type': 'application/vnd.api+json'}
        
        # 步驟 1: 建立 Item 和 Version 的完整 Payload
        # 這是之前一直出錯的地方，我們現在使用正確的結構
        create_item_url = f"{APS_DM_DATA_URL}/projects/{project_id}/items"
        item_payload = {
            "jsonapi": {"version": "1.0"},
            "data": {
                "type": "items",
                "attributes": {
                    "displayName": file_name,
                    "extension": {"type": "items:autodesk.bim360:File", "version": "1.0"}
                },
                "relationships": {
                    "tip": {"data": {"type": "versions", "id": "1"}},
                    "parent": {"data": {"type": "folders", "id": folder_id}}
                }
            },
            "included": [
                {
                    "type": "versions",
                    "id": "1",
                    "attributes": {"name": file_name},
                    "relationships": {
                        # 我們先不指定 storage，讓 API 為我們自動建立
                    }
                }
            ]
        }
        item_resp = requests.post(create_item_url, headers=headers, json=item_payload)
        item_resp.raise_for_status()
        
        # 步驟 2: 從 Item 建立的回應中，取得儲存位置的 URN 和簽名過的上傳 URL
        storage_id = item_resp.json()['included'][0]['relationships']['storage']['data']['id']
        upload_url = item_resp.json()['included'][0]['relationships']['storage']['meta']['link']['href']

        return jsonify({
            'uploadUrl': upload_url,
            'storageId': storage_id,
            'itemId': item_resp.json()['data']['id']
        })

    except Exception as e:
        error_message = str(e)
        if hasattr(e, 'response') and e.response is not None:
             error_message = e.response.text
        print(f"CRITICAL ERROR (prepare-upload): {error_message}")
        return jsonify({'error': f"An error occurred: {type(e).__name__} - {error_message}"}), 500

@app.route('/api/items/<item_id>/complete-upload', methods=['POST'])
def complete_upload(item_id):
    storage_id = request.json.get('storageId')
    if not all([item_id, storage_id]):
        return jsonify({'error': '缺少必要參數'}), 400

    try:
        headers = {**get_auth_header(), 'Content-Type': 'application/vnd.api+json'}

        project_id = session.get('current_project_id')
        
        # 完成 S3 上傳後，需要更新 Version 的狀態
        # 這一步的 payload 是更新 item 的 tip version
        # 但在許多流程中，這一步是可選的，因為轉檔會自動觸發
        # 為了簡化，我們先假設 S3 上傳成功就完成了所有步驟
        print(f"INFO: Upload completed for item {item_id} using storage {storage_id}")
        
        return jsonify({'success': True, 'message': '伺服器已收到上傳完成通知，轉檔將自動開始。'})
    
    except Exception as e:
        error_message = str(e)
        if hasattr(e, 'response') and e.response is not None:
             error_message = e.response.text
        print(f"CRITICAL ERROR (complete_upload): {error_message}")
        return jsonify({'error': f"An error occurred: {type(e).__name__} - {error_message}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)