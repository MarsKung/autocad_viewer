import os
import requests
import json
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數 (主要用於本地測試)
load_dotenv()

# 從環境變數讀取金鑰 (在 GitHub Actions 中，這些會由 Secrets 提供)
APS_CLIENT_ID = os.environ.get('APS_CLIENT_ID')
APS_CLIENT_SECRET = os.environ.get('APS_CLIENT_SECRET')
APS_AUTH_URL = 'https://developer.api.autodesk.com/authentication/v2/token'

def get_aps_token():
    """獲取一個具備閱覽權限的 Access Token"""
    print("Requesting a new token from APS...")
    if not all([APS_CLIENT_ID, APS_CLIENT_SECRET]):
        raise ValueError("Client ID or Secret is not set.")
    
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'grant_type': 'client_credentials',
        'client_id': APS_CLIENT_ID,
        'client_secret': APS_CLIENT_SECRET,
        'scope': 'viewables:read data:read'
    }
    response = requests.post(APS_AUTH_URL, headers=headers, data=data)
    response.raise_for_status()
    print("Token successfully retrieved.")
    return response.json()

def main():
    """主執行函數：獲取 token 並寫入檔案"""
    try:
        token_data = get_aps_token()
        
        # 確保 viewer 資料夾存在
        os.makedirs('viewer', exist_ok=True)
        
        # 將 token 寫入 viewer/token.json
        with open('viewer/token.json', 'w') as f:
            json.dump(token_data, f, indent=4)
            
        print("Successfully wrote token to viewer/token.json")
    except Exception as e:
        print(f"An error occurred: {e}")
        # 拋出異常，讓 GitHub Action 知道任務失敗
        raise e

if __name__ == '__main__':
    main()