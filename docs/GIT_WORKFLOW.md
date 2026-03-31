# ProSourcing 项目 Git 开发工作流手册

哥，这是为您准备的 Git 协作指南。遵循这套流程，可以确保您的代码在多人/多任务并行时依然清晰有序。

## 流程概览 (The Loop)

1. **确定 Issue**：从 GitHub 获取要做的任务 ID（如 #9）。
2. **同步主线**：
   ```bash
   git checkout main
   git pull origin main
   ```
3. **开辟战场**：
   ```bash
   git checkout -b feat/9-cat-tree-date
   ```
4. **开发提交**：
   ```bash
   git add .
   git commit -m "feat: 实现品类树日期展示 (#9)"
   git push origin feat/9-cat-tree-date
   ```
5. **提起 PR**：在页面上点击 "Create Pull Request"，标题包含 `#9`。
6. **合流清理**：PR 合并后，立即回到本地：
   ```bash
   git checkout main
   git pull origin main
   git branch -d feat/9-cat-tree-date
   ```

## 多任务并行处理
如果您在处理 Issue #9 时，突然想改 Issue #10：
1. `git stash` (保存当前未完成的改动) 或 `git commit`。
2. `git checkout main`。
3. `git checkout -b feat/10-category-l10n`。
4. 搞定后切回：`git checkout feat/9-cat-tree-date` 并在需要时 `git stash pop`。

## 核心原则
- **不污染 Main**：永远不在本地 main 分支直接写代码。
- **关联 Issue**：Commit Message 尽量带上 `#ID`。
- **合并即弃**：Feature 分支合并后应及时删除，保持分支列表清爽。
