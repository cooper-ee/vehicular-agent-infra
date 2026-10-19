# 导入自己的 GitHub 仓库

ZIP 解压后进入 `vehicular-agent-infra`（应直接看到 pyproject.toml 和 src）。
GitHub 新建空仓库，不勾选自动生成 README、LICENSE 或 .gitignore，然后在本地执行：

```powershell
git init
git add .
git commit -m "Initial research prototype"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/vehicular-agent-infra.git
git push -u origin main
```

替换 YOUR_USERNAME；仓库名也可以自定。GitHub Import repository 页面不直接接收本地 ZIP。
推荐用上述 Git 命令或 GitHub Desktop 的 Add existing repository → Publish repository，确保包含 `.github` 等隐藏目录。
上传前阅读 THIRD_PARTY_NOTICES.md，运行测试，把自己的设备实测放入新的实验目录。
无需上传外层交付目录、其他两个项目、虚拟环境或模型文件。
