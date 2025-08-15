# ベースイメージ（軽量かつPython 3.11）
FROM python:3.11-slim

# 作業ディレクトリの作成
WORKDIR /app

# 依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードのコピー
COPY main.py .

# 環境変数（Northflank側で設定するのでDockerfileには書かない）

# 起動コマンド
CMD ["python", "main.py"]