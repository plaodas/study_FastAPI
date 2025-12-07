# 認証連携（設計ガイド）

目的
- 本番環境で `user_id` を信頼できる形で取得するための設計指針と、FastAPI での実装サンプルを示します。

要点
- クライアント送信の `X-User-Id` 等のヘッダは信頼しない。
- 認証基盤（OAuth2 / OIDC / JWT / SSO など）を導入し、検証済みトークンから `user_id` を取り出す。
- FastAPI の依存注入（`Depends`）で `current_user` を解決し、エンドポイントで利用する。

設計パターン（短い手順）
1. 認証方式を決める（例: JWT を用いた OIDC / 自前の OAuth2）。
2. トークンを検証するミドルウェア／依存関数を実装する。
3. `current_user` を返す依存関数を作り、ユーザ識別子を確実に得る。
4. 監査では `current_user.id`（または username）を使う。ヘッダはログ用の補助情報として扱う。

FastAPI 実装サンプル（JWT を想定した簡易例）
```python
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer
import jwt

security = HTTPBearer()

SECRET = "your-jwt-secret"

def get_current_user(credentials=Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])  # or OIDC jwks
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication")

    user_id = payload.get("sub") or payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user in token")

    # Optionally load user from DB to ensure active/authorized
    # user = db.query(User).filter(User.id == user_id).one_or_none()
    # if not user:
    #     raise HTTPException(status_code=401, detail="User not found")

    return {"id": user_id, "claims": payload}

# 使い方（エンドポイント）
from fastapi import APIRouter

router = APIRouter()

@router.post('/items')
def create_item(..., current_user: dict = Depends(get_current_user)):
    # current_user['id'] を信頼できる user_id として使う
    ...
```

実運用での注意
- トークンの署名検証は必須。OIDC を使う場合は JWKS を取得して検証する。
- リフレッシュトークンや失効リスト（revocation）を扱う場合は追加の検証が必要。
- `current_user` を DB 経由で取得してロールや状態（有効/無効）を確認するのが安全。

データベーススキーマの検討
- `user_id` を文字列のままにするか（UUID/文字列）／整数にするかを決める。
- 整数で `users` テーブルが存在するなら外部キー制約を張ることで整合性を強化できる（追加マイグレーションが必要）。

移行手順のサンプル
1. 認証を実装して `current_user` を返す依存を作成
2. `create_item` 等のエンドポイントを更新して `current_user` を受け取るようにする
3. 既存コードがヘッダから `user_id` を参照している箇所を順次置換
4. （任意）`user_id` を整数化して FK を張る計画がある場合は、マイグレーションで安全に変換する

もし希望があれば、あなたの環境（外部認証プロバイダの有無、JWT or OIDC、ユーザDB の形）に合わせた具体的な実装プランとコードを作成します。
