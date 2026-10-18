# 个人预览版与贡献流程

网页：https://13bit-x.github.io/PoE2_RexTool/

## 分支

- `main`：与 lakemem0ry/PoE2_RexTool 的 main 同步，不直接修改。
- `preview`：个人使用版本，包含尚未被作者合并的修复。Pages 发布这个分支的 HTML。
- `automation`：本 Fork 默认分支，仅维护定时同步与发布配置。
- `fix/问题名称`：从最新 main 创建，每个问题一个分支，向作者的 main 提交 PR。

## 自动更新

每小时第 23 分钟尝试同步作者 main，再合并到 preview 并发布。GitHub 可能延迟运行。
preview 的修改在下一次任务运行时发布；想立即发布，在 Actions 选择
“Sync upstream and publish preview” → Run workflow，分支选 automation。

工作流不使用强制推送。遇到合并冲突、并发修改或 main 已发生分歧时，停止发布，保留已有网页。
到 Actions 查看失败原因，处理 preview 冲突后重新运行。
公开仓库连续 60 天没有仓库活动时，GitHub 可能暂停定时任务，需要重新启用。

## 修复并提交 PR

```sh
git fetch origin
git switch -c fix/问题名称 origin/main
# 修改并验证后提交
git add PoE2_RexTool.html
git commit -m "Fix: 问题描述"
git push -u origin fix/问题名称
```

在 GitHub 向 `lakemem0ry/PoE2_RexTool` 的 `main` 提交 PR。
本 Fork 默认分支是 automation，创建 PR 时请明确选择目标 main。

将已完成的修复并入个人预览版：

```sh
git switch preview
git pull --ff-only origin preview
git merge --no-edit fix/问题名称
git push origin preview
```

然后手动运行发布工作流，或等下一次定时发布。
不要从 preview 向作者提 PR，以免混入其他尚未合并的修复。
作者合并后仍需检查修复行为；若作者采用 squash/rebase 合并，同一区域的后续修改可能需要手动解决冲突。

## 官方文档

- [定时任务规则](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [Pages 自动发布](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
