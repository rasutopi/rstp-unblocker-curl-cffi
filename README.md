セットアップ
```
# これをプロジェクトディレクトリで実行
# Python仮想環境作成
python3 -m venv venv

# 仮想環境有効化
source venv/bin/activate

# pipアップグレード（超重要）
pip install --upgrade pip

# 依存パッケージ一括インストール
pip install -r requirements.txt
```

起動する
```
source venv/bin/activate
python -m uvicorn proxy:app --host 0.0.0.0 --port 8000
```

---

ライセンスは[rstp-unblocker](https://github.com/rasutopi/rstp-unblocker/tree/main)と同じです。
