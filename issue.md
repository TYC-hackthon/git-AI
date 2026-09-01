# Git-like AI Chat 待修復問題與功能規劃清單 (Issues & Roadmap)

本文件彙整 Git-like AI Chat 專案目前發現之系統缺陷 (Bugs)、核心功能擴充 (Feature Requests) 與架構優化清單。

---

## 目錄

- [現存重大問題 (Critical Bugs)](#現存重大問題-critical-bugs)
  - [Issue #1: branch_info.py 中 generate_metadata 因未處理 dict 回傳值導致 strip 崩潰 [已修復]](#issue-1-branch_infopy-中-generate_metadata-因未處理-dict-回傳值導致-strip-崩潰)
  - [Issue #2: branches.py 中 recompute_branch 呼叫參數順序錯誤 [已修復]](#issue-2-branchespy-中-recompute_branch-呼叫參數順序錯誤)
  - [Issue #3: 資料庫 BranchInfo 缺少級聯刪除 (ondelete CASCADE) [已修復]](#issue-3-資料庫-branchinfo-缺少級聯刪除-ondelete-cascade)
- [核心功能擴充 (Feature Requests)](#核心功能擴充-feature-requests)
  - [Issue #4: 支援 SSE (Server-Sent Events) 即時打字機串流輸出 [規劃中]](#issue-4-支援-sse-server-sent-events-即時打字機串流輸出)
  - [Issue #5: 雙分支視覺化對比視窗 (Visual Branch Diff) [已實作]](#issue-5-雙分支視覺化對比視窗-visual-branch-diff)
  - [Issue #6: 智慧合併提交 (LLM Merge Synthesis) [已實作]](#issue-6-智慧合併提交-llm-merge-synthesis)
  - [Issue #7: 具名分支與里程碑標籤系統 (Named Branches & Git Tags) [規劃中]](#issue-7-具名分支與里程碑標籤系統-named-branches--git-tags)
  - [Issue #8: 上下文 Token 預算管理與長對話歷史滑動壓縮 [規劃中]](#issue-8-上下文-token-預算管理與長對話歷史滑動壓縮)
  - [Issue #9: 對話樹關鍵字檢索與標籤過濾導航 [已實作]](#issue-9-對話樹關鍵字檢索與標籤過濾導航)
  - [Issue #10: 跨分支 Cherry-pick 與局部子樹剪枝 (Prune) [規劃中]](#issue-10-跨分支-cherry-pick-與局部子樹剪枝-prune)
  - [Issue #11: 支援各分支獨立設定 System Prompt [規劃中]](#issue-11-支援各分支獨立設定-system-prompt)
- [架構健全性與測試 (Engineering & Quality)](#架構健全性與測試-engineering--quality)
  - [Issue #12: 建立後端 DAG 與上下文重組核心演算法之單元測試套件 [已完成]](#issue-12-建立後端-dag-與上下文重組核心演算法之單元測試套件)

---

## 現存重大問題 (Critical Bugs)

### Issue #1: branch_info.py 中 generate_metadata 因未處理 dict 回傳值導致 strip 崩潰
- **類型**: Bug (Defect)
- **優先級**: P0 (最高，阻礙主要流程)
- **影響範圍**: Backend ([`branch_info.py`](file:///home/ysh/git-AI/Backend/app/services/branch_info.py#L48-L51), [`providers.py`](file:///home/ysh/git-AI/Backend/app/services/providers.py#L166-L175))
- **問題描述**:
  在 [`branch_info.py`](file:///home/ysh/git-AI/Backend/app/services/branch_info.py) 的 `generate_metadata` 函式中呼叫了 `provider_reply(provider, model, messages, base_url)`。當 `provider` 為 `"ollama"` 時，[`providers.py`](file:///home/ysh/git-AI/Backend/app/services/providers.py) 的 `chat_with_ollama()` 回傳型態為 `dict`（內含 `content`, `total_tokens` 等），接續執行 `response_text.strip()` 會拋出 `AttributeError: 'dict' object has no attribute 'strip'`。此錯誤導致非同步背景任務在所有 Ollama 對話後皆無法生成標籤與摘要。
- **預期行為**:
  正確提取回應文字，相容回傳為字串或字典的情況：
  ```python
  raw_text = response_text.get("content", "") if isinstance(response_text, dict) else str(response_text)
  clean_text = raw_text.strip()
  ```

---

### Issue #2: branches.py 中 recompute_branch 呼叫參數順序錯誤
- **類型**: Bug (Defect)
- **優先級**: P0 (最高)
- **影響範圍**: Backend ([`branches.py`](file:///home/ysh/git-AI/Backend/app/blueprints/branches.py#L160))
- **問題描述**:
  在 [`branches.py`](file:///home/ysh/git-AI/Backend/app/blueprints/branches.py#L160) 中的 `recompute_branch` 路由內呼叫了：
  ```python
  upsert_branch_info(node_id, user.id, ollama_base_url)
  ```
  但 [`branch_info.py`](file:///home/ysh/git-AI/Backend/app/services/branch_info.py#L79) 中函式簽名定義為：
  ```python
  def upsert_branch_info(node_id: int, user_id: int, provider: str = "ollama", metadata_model: str | None = None, ollama_base_url: str | None = None):
  ```
  這導致 `ollama_base_url` 被當成第三個位置引數 `provider`，引發後續 Provider 判定錯誤。
- **預期行為**:
  改為具名引數傳遞：
  ```python
  upsert_branch_info(node_id, user.id, ollama_base_url=ollama_base_url)
  ```

---

### Issue #3: 資料庫 BranchInfo 缺少級聯刪除 (ondelete CASCADE)
- **類型**: Bug / Database Integrity
- **優先級**: P0
- **影響範圍**: Backend ([`models.py`](file:///home/ysh/git-AI/Backend/app/models.py#L64-L76), [`conversations.py`](file:///home/ysh/git-AI/Backend/app/blueprints/conversations.py#L60))
- **問題描述**:
  [`models.py`](file:///home/ysh/git-AI/Backend/app/models.py) 的 `BranchInfo` 表對 `message_nodes.id` 的外鍵關聯未加上 `ondelete="CASCADE"`。當執行清空使用者對話（[`conversations.py`](file:///home/ysh/git-AI/Backend/app/blueprints/conversations.py#L60) 中的 `DELETE FROM message_nodes`）或管理者刪除使用者資料時，如果資料庫開啟外鍵檢查會引發 `IntegrityError`；若未開啟則會留下無主的孤立 Embedding 紀錄。
- **預期行為**:
  1. 在 `BranchInfo` 的 `node_id` 外鍵加上 `ForeignKey("message_nodes.id", ondelete="CASCADE")`。
  2. 在刪除 `MessageNode` 時一併刪除對應的 `BranchInfo`。

---

## 核心功能擴充 (Feature Requests)

### Issue #4: 支援 SSE (Server-Sent Events) 即時打字機串流輸出
- **類型**: Feature / UX
- **優先級**: P1
- **影響範圍**: Fullstack (Backend [`chat.py`](file:///home/ysh/git-AI/Backend/app/blueprints/chat.py), [`providers.py`](file:///home/ysh/git-AI/Backend/app/services/providers.py); Frontend [`ConversationPanel.vue`](file:///home/ysh/git-AI/Frontend/src/components/chat/ConversationPanel.vue), [`index.vue`](file:///home/ysh/git-AI/Frontend/src/pages/index.vue))
- **功能動機**:
  目前後端是等 Ollama/Gemini 全部文字生成完畢後一次性回傳 JSON，前端必須等待 10 至 60 秒僅顯示旋轉進度條。改為串流輸出能顯著改善用戶體感回應延遲。
- **規格規劃**:
  1. 後端新增串流端點 `POST /api/chat/stream`，以 `text/event-stream` 格式逐塊推送 token，並在最後一個事件附帶完整生成之 node id 與 token 使用統計。
  2. 前端改用 `fetch` 的 `ReadableStream` 接收 chunk，即時增量更新當前氣泡，配合 [`MessageRenderer.vue`](file:///home/ysh/git-AI/Frontend/src/components/chat/MessageRenderer.vue) 動態解析渲染。

---

### Issue #5: 雙分支視覺化對比視窗 (Visual Branch Diff)
- **類型**: Feature / Git Workflows
- **優先級**: P1
- **影響範圍**: Fullstack (Backend [`branches.py`](file:///home/ysh/git-AI/Backend/app/blueprints/branches.py); Frontend [`BranchPanel.vue`](file:///home/ysh/git-AI/Frontend/src/components/chat/BranchPanel.vue), [`index.vue`](file:///home/ysh/git-AI/Frontend/src/pages/index.vue))
- **功能動機**:
  目前「Compare similarity」按鈕僅以原生 `window.alert()` 呈現餘弦相似度小數，缺少視覺化差異。
- **規格規劃**:
  1. 後端新增 `GET /api/branches/diff?node_a=<id>&node_b=<id>` 端點：
     - 自動計算並回傳兩節點的最近共同祖先節點 (Lowest Common Ancestor, LCA)。
     - 分別列出自 LCA 起至 Node A 與 Node B 各自演變的訊息鏈 (Divergent History)。
  2. 前端以彈窗或抽屜呈現 Side-by-side 並排對照視窗，清楚呈現分歧點與各分支重點。

---

### Issue #6: 智慧合併提交 (LLM Merge Synthesis)
- **類型**: Feature / AI Core
- **優先級**: P1
- **影響範圍**: Backend ([`chat.py`](file:///home/ysh/git-AI/Backend/app/blueprints/chat.py#L131), [`message_nodes.py`](file:///home/ysh/git-AI/Backend/app/services/message_nodes.py#L229))
- **功能動機**:
  目前 `POST /api/merge` 產生的合併節點僅放入固定文字 (`"I'm now bringing in context..."`)，模型缺乏對雙方分支討論結果的融會貫通。
- **規格規劃**:
  1. 呼叫 LLM 綜合分析 Branch A 與 Branch B 兩個分支的脈絡與成果，產出一份結構化的「合併摘要與共識結論」。
  2. 將該摘要作為 Merge Node 的 Assistant 內容保存，作為後續延伸對話的清晰基礎。
  3. 提供多種合併策略切換：`synthesize`（AI 總結融合）、`sequential`（循序交錯保留）、`selective`（自選關鍵節點）。

---

### Issue #7: 具名分支與里程碑標籤系統 (Named Branches & Git Tags)
- **類型**: Feature / Git Workflows
- **優先級**: P1
- **影響範圍**: Fullstack (Backend [`models.py`](file:///home/ysh/git-AI/Backend/app/models.py), [`branches.py`](file:///home/ysh/git-AI/Backend/app/blueprints/branches.py); Frontend [`BranchPanel.vue`](file:///home/ysh/git-AI/Frontend/src/components/chat/BranchPanel.vue))
- **功能動機**:
  目前對話分支僅以 `Conversation 1` 或 `Node #ID` 呈現，分支一多時難以分辨。
- **規格規劃**:
  1. 允許使用者為葉節點或任意節點自訂分支名稱（例如 `feature/auth-jwt`、`exp/redis-cache`）。
  2. 支援打上 Git Tag 標記（如 `v1.0-solution`、`milestone`），在樹狀圖上以徽章顯示，點選可直接切換上下文。

---

### Issue #8: 上下文 Token 預算管理與長對話歷史滑動壓縮
- **類型**: Feature / Context Management
- **優先級**: P2
- **影響範圍**: Backend ([`message_nodes.py`](file:///home/ysh/git-AI/Backend/app/services/message_nodes.py#L61))
- **功能動機**:
  在深層分支或經多次合併的節點中，由 [`rebuild_context_nodes`](file:///home/ysh/git-AI/Backend/app/services/message_nodes.py#L61) 回溯的所有祖先訊息總量極易超出 LLM Context Window，引發推論失敗或高額 Token 負擔。
- **規格規劃**:
  1. 加入 Token 計算與預算上限檢查。
  2. 超出 Token 預算時啟用自動壓縮策略：保留根節點與最近 $N$ 輪完整對話，中間過長的早期歷史自動透過 LLM 壓縮成一則系統摘要。

---

### Issue #9: 對話樹關鍵字檢索與標籤過濾導航
- **類型**: Feature / UI
- **優先級**: P2
- **影響範圍**: Frontend ([`BranchPanel.vue`](file:///home/ysh/git-AI/Frontend/src/components/chat/BranchPanel.vue))
- **功能動機**:
  對話節點變多時，用戶不易在縱向樹狀圖中定位曾討論過特定主題的節點。
- **規格規劃**:
  1. 在樹狀面板上方增加搜尋輸入框，輸入文字時即時高亮匹配的對話節點。
  2. 提取 [`BranchInfo.tags`](file:///home/ysh/git-AI/Backend/app/models.py#L80) 生成標籤過濾列，點選特定標籤（例如 `#python`, `#refactor`）即可篩選關聯分支。

---

### Issue #10: 跨分支 Cherry-pick 與局部子樹剪枝 (Prune)
- **類型**: Feature / Advanced Git
- **優先級**: P2
- **影響範圍**: Fullstack (Backend & Frontend)
- **功能動機**:
  進一步完善 Git 精神：允許擷取其他分支的精準回答，並允許清理無效對話。
- **規格規劃**:
  1. **Cherry-pick**: 允許在瀏覽其他分支時，選取特定問答節點並將其「挑選複製」追加至目前對話分支底部。
  2. **Prune (子樹剪枝)**: 允許刪除某節點及其底下的所有子節點，而不會波及其他平行分支。

---

### Issue #11: 支援各分支獨立設定 System Prompt
- **類型**: Feature / Context Management
- **優先級**: P2
- **影響範圍**: Fullstack (Backend [`models.py`](file:///home/ysh/git-AI/Backend/app/models.py); Frontend [`ModelSettingsPanel.vue`](file:///home/ysh/git-AI/Frontend/src/components/chat/ModelSettingsPanel.vue))
- **功能動機**:
  進行對照實驗時，不同分支通常需要不同的提示詞約束（例如一個分支約束用 Python，另一個用 Rust）。目前 System Prompt 是全域設定，無法依分支保留各自設定。
- **規格規劃**:
  1. 將 `system_prompt` 關聯至分支或節點中儲存。
  2. 切換分支時自動切換並呈現該分支專屬的 System Prompt。

---

## 架構健全性與測試 (Engineering & Quality)

### Issue #12: 建立後端 DAG 與上下文重組核心演算法之單元測試套件
- **類型**: Test / Quality Assurance
- **優先級**: P2
- **影響範圍**: Backend
- **功能動機**:
  [`rebuild_context_nodes`](file:///home/ysh/git-AI/Backend/app/services/message_nodes.py#L61) 涉及多重父節點、合併節點、菱形繼承與防循環邏輯，是整個系統最核心的靈魂模組，需有自動化測試防護。
- **規格規劃**:
  1. 使用 `pytest` 建立單元測試集。
  2. 針對線性對話回溯、分支交叉、多重 Merge、循環偵測拋出例外等各種拓撲結構撰寫測試案例。
