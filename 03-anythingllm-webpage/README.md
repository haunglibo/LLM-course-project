# 03 - AnythingLLM Webpage

一个单文件网页，调用 AnythingLLM 的文档上传接口，把本地文档上传到指定工作区并自动完成向量化嵌入。

## 依赖

- AnythingLLM 桌面版或服务端已启动，默认地址 `http://localhost:3001`
- 一个有效的 AnythingLLM API Key（可在 AnythingLLM 的「设置 → API Keys」中创建）

## 运行

```powershell
cd 03-anythingllm-webpage
python -m http.server 8000
```

浏览器打开 <http://localhost:8000/upload.html>，填入 API Key、选择文件，点击「上传并向量化」。

## 实现说明

- 接口：`POST http://localhost:3001/api/v1/document/upload`
- 请求方式：`multipart/form-data`
  - `file`：待上传的文件
  - `addToWorkspaces`：目标工作区的 slug（逗号分隔），传入后 AnythingLLM 会自动解析并向量化
- 鉴权：请求头 `Authorization: Bearer <API Key>`
- 页面顶部 `WORKSPACE` 常量需替换为你自己的第一个工作区 slug

## 安全提示

API Key 不在代码中硬编码，由使用者在页面输入框中填写。
