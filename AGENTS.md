# 專案總覽：Git-like AI 聊天室

本專案旨在解決 LLM 上下文污染問題。透過樹狀結構 (Tree/DAG) 管理對話節點，允許使用者回到過去的節點開啟新分支，並精準控制傳遞給模型的上下文。

專案架構：

- Root (此目錄)：全局管理與跨端規格。
- Frontend/ (Submodule)：Vue 3 前端介面與狀態管理。
- Backend/ (Submodule)：Flask 後端與 SQLAlchemy 資料庫。

## 啟動與驗證

標準啟動方式：

```bash
./start-dev.sh
```

啟動後服務位置：

- Backend: `http://127.0.0.1:5000`
- Frontend: `http://127.0.0.1:3000`
- Vite proxy: 前端 `/api` 會代理到 Backend `http://localhost:5000`

驗證指令：

```bash
cd Frontend && npm run build
cd Backend && python3 -m py_compile main.py core/general.py core/log.py core/web.py
```

注意：目前 `npm run lint` 依賴支援 `Object.groupBy` 的 Node 執行環境；Node `v20.20.2` 會因缺少 `Object.groupBy` 而失敗。

## 絕對禁令 (Global Constraints)

1. 嚴格禁止 Emoji：在任何產出的程式碼 (Python, JS, TS, Vue 等) 與 Git Commit Message 中，絕對不增添任何 emoji。
2. 零臆測原則：若 API 規格、欄位名稱或路徑資訊不足，不准根據慣例瞎猜，必須直接詢問使用者以確認細節。

## 跨端協作守則 (Execution Protocol)

作為全端 AI 助手，你擁有全局讀取權限，但必須嚴格遵守「單點寫入」原則：

1. 讀取 (Read-Only) 許可：鼓勵你跨目錄讀取另一個 Submodule 的程式碼（例如寫後端時去讀前端的 API 呼叫結構），以確保參數一致性。
2. 寫入 (Write) 隔離：除非使用者明確要求「請同時修改前後端」，否則單次任務中，僅允許修改目標 Submodule 的程式碼，絕對不可越界修改另一端的檔案。

---

## [Mode: Frontend] 前端開發規範

當使用者的任務涉及 `Frontend/` 時，請切換至此模式：

- 技術棧：Vue 3 (Composition API), Vite。
- 核心任務：
  1. 對話樹 (Tree) 視覺化：使用輕量級方式呈現節點與分支狀態。
  2. 狀態管理：精準維護 `currentNodeId`，點擊圖表節點時觸發狀態更新，並重新請求該節點的完整線性上下文。
  3. API 串接：發送新訊息時，必須在 Payload 中夾帶 `parent_id` (即目前的 `currentNodeId`)。

## [Mode: Backend] 後端開發規範

當使用者的任務涉及 `Backend/` 時，請切換至此模式：

- 技術棧：Python Flask, SQLAlchemy, Ollama (Local LLM)。
- 核心資料結構：
  - `MessageNode` 表：包含 `id`, `parent_id` (指向上一句對話), `role` (user/assistant), `content`。
- 核心任務：
  1. 上下文重組演算法 (Context Rebuilder)：接收到特定的 `node_id` 時，透過資料庫遞迴向上追溯所有的 `parent_id` 直到根節點。將收集到的節點反轉順序，組合出標準的 `[{"role": "user", "content": "..."}, ...]` 陣列。
  2. Ollama 串接：將重組後的上下文陣列傳送給 Ollama 服務 (可使用官方 `ollama-python` 套件或直接發送 HTTP 請求至 `localhost:11434`)。
  3. 分支建立 (Commit)：將使用者的輸入與 Ollama 的回覆依序存入資料庫，確保新的 `parent_id` 鏈結正確。

## 版本控制規範

本專案使用 ***submodule*** 形式開發，再更新 ***Frontend***, ***Backend*** 任一後，請回到 ***Root Repository*** ***commit*** 並 ***push*** ，正式網頁會以 ***Root Repository*** 所看到的版本為主。 因此請注意 ***Frontend*** 及 ***Backend*** 版本的同步。

### Pull

當提取原端修改時，請執行

```bash
git pull --all
git submodule update
```

### Push

當提交 ***commit*** 時，請執行

```bash
# You're now in Frontend / Backend directory
# Commit for each repo you've modified
git add --all
git commit -m"..."
git push

# Return to Root Repository
cd ..
git submodule update --remote
git commit -m"..."
git push

# Use tag if you belive this is a major modified version
git tag A.B.C # Shame-style tag version code
git push --tags
```

### Commit

請注意在簽出的時候，訊息必須遵守以下規範：

```
[Major of this change like, `Update user interface` or `Bugs fix`]

# List all the changes you've made in this format
 - [ADD] ...
 - [MODIFY] ...
 - [REMOVE] ...
 - [MAINTAIN] ...
 - [NOTE] ...
 - [TEST] ...
```