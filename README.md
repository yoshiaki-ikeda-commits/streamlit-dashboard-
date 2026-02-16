# Streamlit Dashboard（スマレジ売上ダッシュボード - 銀座）

## 概要

銀座店舗のスマレジ売上データを可視化する Streamlit ダッシュボード。日別・月別売上推移、商品ランキング、カテゴリ別売上、曜日x時間帯ヒートマップを前年比較付きで表示する。

## 技術スタック

- **フレームワーク**: Streamlit
- **チャート**: Plotly
- **データ処理**: pandas
- **DB**: Supabase (PostgreSQL)
- **言語**: Python 3

## 主な機能

- KPI カード（売上合計・取引件数・客単価・商品点数 + 前年同期比較）
- 日別売上推移（前年同期オーバーレイ）
- 月別売上サマリー
- 商品ランキング TOP20
- カテゴリ別売上円グラフ
- 曜日 x 時間帯 売上ヒートマップ
- サイドバーでの日付範囲フィルター

## 環境変数

`.env` に以下を設定:

```
SUPABASE_URL=
SUPABASE_KEY=
```

## セットアップ

```bash
pip install -r requirements.txt
cp .env.example .env
# .env に Supabase のキーを設定
streamlit run app.py
```

http://localhost:8501 で起動。

## デプロイ

Streamlit Community Cloud でのデプロイに対応。`st.secrets` で環境変数を管理可能。
