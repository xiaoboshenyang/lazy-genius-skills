# 打工人 Skill 系列计划

> 这个目录未来也是本地仓库根目录（Gitee 主仓 + GitHub 镜像）。

---

## 定位

每篇公众号文章配一个 skill，文章即安装引导。
读者打开文章 → 跟着对话配置 → 当场能用。

目标：**打工人 80 个 AI 工具包**

---

## 仓库规划

```
skill-pack/               ← 本目录即仓库根
├── README.md             ← 分类索引 + 安装说明
├── 新媒体/
│   ├── wechat-publisher/
│   ├── douyin-extract/
│   └── ljg-card/
├── 财务/
│   ├── expense-report/
│   └── invoice-reader/
├── 效率工具/
│   ├── meeting-notes/
│   └── email-writer/
└── 基础工具/
    └── ...
```

托管：Gitee 主仓，GitHub 同步镜像。

---

## Skill 设计规范

### 每个 skill 必须包含

1. **SKILL.md** — skill 本体
2. **setup 流程** — 首次检测到缺 key，自动进入配置向导，对话式引导完成
3. **AskUserQuestion** — 关键节点确认，不让用户猜

### Key 管理原则

- key 不写进 SKILL.md，只写「去哪申请 + 存到哪」
- skill 执行时从环境变量读取
- 仓库可公开

### 常用工具组合（allowed-tools 参考）

- 只读分析：`Read, Glob, Grep`
- 文件处理：`Read, Write, Edit`
- 交互引导：`Read, Write, Edit, AskUserQuestion`
- 需要跑命令：加 `Bash`
- 需要联网：加 `WebFetch` 或 `WebSearch`

---

## 内容策略

- 每篇文章 = 一个 skill 的安装 + 使用教程
- 文章即引导，不另写图文文档
- 优先做「不需要梯子、普通打工人有痛点」的 skill

### 系列规划

**第一系列：新媒体爆款提取**（已有 skill 基础，优先启动）

| 期数 | 平台 | Skill 状态 | 文章状态 |
|------|------|-----------|---------|
| ① | 公众号 | 已有（日报提取） | 待写 |
| ② | 抖音 | 已有（抖音提取） | 待排期 |
| ③ | 小红书 | 待开发 | 待排期 |
| … | 其他平台 | 待规划 | — |

后续系列待定，由博书拍板。

---

## 现有可直接归入的 skill

（位于 `.claude/skills/`，迁移时按分类放入对应文件夹）

- 新媒体：humanizer-zh, ljg-card, wechat-draft-publisher, style-writer, text-to-visual, douyin-extract, wechat-single-extract
- 效率工具：录音清洗, 录音清洗
- 文档生产：docx, pdf, pptx, xlsx

---

## 生图分支（Nano API）

> 用 Claude + Nano API 做图，不需要额外订阅 Midjourney / Stable Diffusion。

### 定位

「用对话生图」——描述需求，直接出图，适合不懂设计的打工人。

### 仓库位置

```
skill-pack/
└── 生图/
    ├── ecom-image/       ← 电商主图/详情图
    ├── wechat-image/     ← 公众号配图/封面
    ├── svg-card/         ← SVG 卡面（可缩放，适合印刷/分享）
    └── html-card/        ← HTML 卡片（网页截图，样式灵活）
```

### 各 Skill 规划

| Skill | 场景 | 输出格式 | 优先级 |
|-------|------|---------|-------|
| ecom-image | 白底主图、场景图、详情页切片 | PNG/JPG | ★★★ |
| wechat-image | 文章封面（900×383）、正文配图 | PNG | ★★★ |
| svg-card | 金句卡、知识卡、名片 | SVG | ★★ |
| html-card | 数据报告卡、活动海报、朋友圈图 | HTML→截图 | ★★ |

### 技术路线

- **图像生成**：Nano API（`imagen` 或对应模型）
- **SVG/HTML 卡片**：Claude 直接生成代码，截图用 `agent-browser` 或 `ljg-card` 流程
- **Key 管理**：NANO_API_KEY 存环境变量，skill 内自动检测 + 配置向导

### 系列文章规划

| 期数 | Skill | 文章角度 | 状态 |
|------|-------|---------|------|
| ① | wechat-image | 公众号封面 5 分钟搞定 | 待开发 |
| ② | ecom-image | 电商主图不花钱 | 待开发 |
| ③ | html-card | 朋友圈海报自己做 | 待开发 |
| ④ | svg-card | 金句卡批量生产 | 待开发 |

### 注意点

- Nano API 图像质量与提示词强相关，skill 内置「提示词增强」步骤
- 电商图需支持背景色/尺寸参数化（1:1 / 3:4 / 16:9）
- HTML 卡片依赖截图能力，需确认 `agent-browser` 可用性
