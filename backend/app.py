# backend/app.py
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import google.generativeai as genai # Gemini API用ライブラリをインポート
from flask_cors import CORS # CORS拡張をインポート

app = Flask(__name__) # Flaskアプリケーションのインスタンスを作成
CORS(app) # 全てのオリジンからのCORSリクエストを許可 (プロトタイプ用)

# データベース設定
# 環境変数 'DATABASE_URL' からデータベース接続URIを取得します。
# これにより、データベースの接続情報をコードに直接書き込まずに済み、
# 環境（開発、本番など）に応じて簡単に切り替えられます。
# 例: "postgresql://user:password@host:port/dbname"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
# SQLAlchemyのイベントシステムを追跡しない設定（メモリ使用量を抑えるため）
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app) # SQLAlchemyのインスタンスを作成し、Flaskアプリと紐付け

# Gemini APIキーの設定
# 環境変数 'GEMINI_API_KEY' からAPIキーを取得します。
# これもセキュリティと環境ごとの切り替えのために重要です。
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    # APIキーが設定されていない場合は警告を出力
    print("GEMINI_API_KEY 環境変数が設定されていません！")
else:
    # APIキーを設定してGemini APIクライアントを初期化
    genai.configure(api_key=GEMINI_API_KEY)

# --- データベースモデルの定義 ---
# Pythonのクラスとしてデータベースのテーブルを表現します (ORM: Object-Relational Mapping)。

class User(db.Model):
    __tablename__ = 'users' # データベース内のテーブル名を指定
    id = db.Column(db.Integer, primary_key=True) # 主キー、自動インクリメント
    username = db.Column(db.String(80), unique=True, nullable=False) # ユーザー名、ユニークでNULL不可
    password_hash = db.Column(db.String(120), nullable=False) # パスワード（プロトタイプではハッシュ化なし）
    # created_at は Supabase側でDEFAULT NOW() で自動設定されるため、ここでは定義しないか、nullable=Trueにする

    def __repr__(self):
        return f'<User {self.username}>' # オブジェクトの文字列表現

class LearningProgress(db.Model):
    __tablename__ = 'learning_progress' # データベース内のテーブル名を指定
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False) # ユーザーテーブルへの外部キー
    # ondelete='CASCADE' は、ユーザーが削除されたら関連する進捗も削除する設定
    content_id = db.Column(db.String(255), nullable=False) # 学習コンテンツの識別子（URLなど）、NULL不可
    completed = db.Column(db.Boolean, default=False) # 完了したかどうか、デフォルトはFalse
    feedback = db.Column(db.Integer, nullable=True) # 1-5段階評価、NULL可
    # created_at は Supabase側でDEFAULT NOW() で自動設定されるため、ここでは定義しないか、nullable=Trueにする
    # UNIQUE (user_id, content_id) はSupabase側で設定済みを前提とするか、SQLAlchemyで複合ユニーク制約を追加

    def __repr__(self):
        return f'<Progress User:{self.user_id} Content:{self.content_id}>'

# データベーステーブルの作成 (アプリケーション起動時に実行されるが、本番ではマイグレーション推奨)
# Supabaseで手動作成済みを前提とするか、このブロックを有効にしてアプリケーション起動時に作成を試みる。
# with app.app_context():
#     db.create_all()
#     print("データベーステーブルが作成または既に存在します。")

# --- APIエンドポイントの定義 ---
# @app.route() デコレータを使って、特定のURLパスとHTTPメソッドに対応する関数を定義します。

@app.route('/')
def hello():
    """ルートパスへのアクセス時の応答"""
    return "スキルアップ・ナビ バックエンド稼働中！ (本番環境)"

@app.route('/register', methods=['POST'])
def register():
    """
    ユーザー登録APIエンドポイント。
    JSON形式でユーザー名とパスワードを受け取り、新しいユーザーをデータベースに保存します。
    プロトタイプのため、パスワードのハッシュ化は行っていません。
    """
    data = request.get_json() # リクエストボディからJSONデータを取得
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"message": "ユーザー名とパスワードが必要です"}), 400 # Bad Request

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return jsonify({"message": "このユーザー名は既に存在します"}), 409 # Conflict

    new_user = User(username=username, password_hash=password) # パスワードは平文で保存 (プロトタイプ用)
    db.session.add(new_user) # データベースセッションに追加
    db.session.commit() # 変更をコミットしてデータベースに保存
    return jsonify({"message": "ユーザー登録が完了しました", "user_id": new_user.id}), 201 # Created

@app.route('/login', methods=['POST'])
def login():
    """
    ユーザーログインAPIエンドポイント。
    JSON形式でユーザー名とパスワードを受け取り、認証を行います。
    プロトタイプのため、簡易的なパスワードチェックです。
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    # ユーザーが存在し、パスワードが一致すればログイン成功
    if user and user.password_hash == password:
        return jsonify({"message": "ログイン成功", "user_id": user.id, "username": user.username}), 200 # OK
    return jsonify({"message": "ユーザー名またはパスワードが間違っています"}), 401 # Unauthorized

@app.route('/recommend_content', methods=['POST'])
def recommend_content():
    """
    AIによる学習コンテンツ提案APIエンドポイント。
    ユーザーの興味を受け取り、Google Gemini APIを呼び出してコンテンツを提案します。
    """
    data = request.get_json()
    user_interest = data.get('interest')
    user_id = data.get('user_id')

    if not user_interest or not user_id:
        return jsonify({"message": "興味とユーザーIDが必要です"}), 400

    if not GEMINI_API_KEY:
        return jsonify({"message": "AIサービスが設定されていません (APIキー不足)"}), 500

    try:
        # Gemini APIモデルを初期化 ('gemini-pro'はテキスト生成に適したモデル)
        model = genai.GenerativeModel('gemini-pro')
        # AIへのプロンプトを作成
        prompt = f"ユーザーは「{user_interest}」に興味があります。大学生向けに、この分野の学習を始めるためのYouTube動画やQiita記事のリンクを3つ提案してください。各リンクは簡単な説明とともに箇条書きで示してください。例：\n- [動画タイトル](URL): 説明\n- [記事タイトル](URL): 説明"

        # Gemini APIを呼び出してコンテンツを生成
        response = model.generate_content(prompt)
        ai_response_text = response.text # AIの応答テキストを取得

        # AIの応答をパースして整形（簡易的な例）
        # AIが生成したテキストから、箇条書きのリンク形式の行を抽出します。
        suggested_contents = []
        lines = ai_response_text.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('- ['): # Markdownの箇条書き形式を想定
                suggested_contents.append(line)

        if not suggested_contents:
            # AIが期待通りの形式で応答しなかった場合のフォールバック
            return jsonify({"message": "AIからの提案を生成できませんでした。別のキーワードでお試しください。", "suggestions": []}), 200

        return jsonify({"message": "コンテンツを提案しました", "suggestions": suggested_contents}), 200

    except Exception as e:
        # API呼び出し中のエラーをキャッチし、エラーメッセージを返す
        print(f"Gemini API呼び出しエラー: {e}")
        return jsonify({"message": "AIサービスに接続できませんでした。APIキーやネットワーク接続を確認してください。", "error": str(e)}), 500

@app.route('/update_progress', methods=['POST'])
def update_progress():
    """
    学習進捗の更新APIエンドポイント。
    ユーザーID、コンテンツID、完了状態、フィードバックを受け取り、データベースを更新します。
    """
    data = request.get_json()
    user_id = data.get('user_id')
    content_id = data.get('content_id')
    completed = data.get('completed', False) # デフォルトはFalse
    feedback = data.get('feedback')

    if not user_id or not content_id:
        return jsonify({"message": "ユーザーIDとコンテンツIDが必要です"}), 400

    if len(content_id) > 255: # content_idが長すぎる場合を考慮し、切り詰める
        content_id = content_id[:255]

    # 既存の進捗エントリを検索
    progress = LearningProgress.query.filter_by(user_id=user_id, content_id=content_id).first()
    if progress:
        # 既存のエントリがあれば更新
        progress.completed = completed
        progress.feedback = feedback
    else:
        # なければ新規作成
        new_progress = LearningProgress(user_id=user_id, content_id=content_id, completed=completed, feedback=feedback)
        db.session.add(new_progress)
    db.session.commit() # 変更をコミット
    return jsonify({"message": "学習進捗を更新しました"}), 200

@app.route('/get_progress/<int:user_id>', methods=['GET'])
def get_progress(user_id):
    """
    特定のユーザーの学習進捗を取得するAPIエンドポイント。
    """
    progress_list = LearningProgress.query.filter_by(user_id=user_id).all()
    result = []
    # 取得した進捗データを辞書形式に変換してリストに追加
    for p in progress_list:
        result.append({
            "content_id": p.content_id,
            "completed": p.completed,
            "feedback": p.feedback
        })
    return jsonify({"progress": result}), 200

if __name__ == '__main__':
    # このブロックはローカル開発環境でのみ実行されます。
    # 本番環境ではGunicornなどのWSGIサーバーがFlaskアプリケーションを起動します。
    # Dockerコンテナ内で実行されるため、ホストは'0.0.0.0'（全てのネットワークインターフェース）に設定します。
    app.run(debug=True, host='0.0.0.0', port=5000)
