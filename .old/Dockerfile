# 使用官方的輕量級 Python 3.9 映像檔
FROM python:3.9-slim

# 設定容器內的工作目錄
WORKDIR /app

# 複製依賴列表並安裝
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 將應用程式的所有檔案複製到容器中
COPY . .

# 向 Docker 聲明容器將使用的埠號 (由 Gunicorn 決定)
EXPOSE 8000

# 容器啟動時，使用 Gunicorn 來運行 Flask 應用
# --workers 3 是一個範例，您可以根據您伺服器的 CPU 核心數調整
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "app:app"]