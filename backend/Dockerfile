# backend/Dockerfile
FROM python:3.9-slim-buster # Python 3.9の軽量なDebianベースイメージを使用

WORKDIR /app # コンテナ内の作業ディレクトリを /app に設定

# requirements.txt をコンテナにコピーし、依存関係をインストール
# これにより、アプリケーションコードをコピーする前に依存関係のレイヤーをキャッシュできます
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt # キャッシュを使わずに依存関係をインストール

COPY . . # 現在のディレクトリ（backend/）の全てのファイルをコンテナの /app にコピー

EXPOSE 5000 # コンテナの5000番ポートを公開することを宣言（情報提供のみ）

# 本番環境でFlaskアプリケーションを起動するためのコマンド
# Gunicornを使って、0.0.0.0:5000で 'app' モジュールの 'app' オブジェクトを起動します。
# CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
# ローカル開発で python app.py を使いたい場合は上記をコメントアウトし、以下を有効にする
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
