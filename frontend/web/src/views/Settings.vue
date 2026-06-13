<script setup lang="ts">
import { NCard, NSpace, NButton, NAlert, NDivider, NCode, useMessage } from 'naive-ui'

const message = useMessage()

function clearAuth() {
  localStorage.removeItem('basic_auth')
  message.success('已清除，刷新后重新输入')
  setTimeout(() => window.location.reload(), 500)
}

const secretsExample = `# 必需 Secrets
TEMPMAIL_BASE_URL = https://mail.Minecraft-cn.net
WEBHOOK_URL       = http://你的VPS_IP:8080/api/webhook/accounts
WEBHOOK_SECRET    = <与前端 ADMIN/Webhook Secret 一致>`

const workflowExample = `# 在 GitHub 仓库的 Actions 页面，点击 Run workflow
# Inputs:
#   count       = 注册数量（建议 5-10）
#   concurrency = 并发数（建议 2-3）`
</script>

<template>
  <NCard title="设置与帮助">
    <NSpace vertical size="large">
      <div>
        <h3 style="margin: 0 0 8px;">认证管理</h3>
        <p style="margin: 0 0 12px; color: #999;">当前 Basic Auth 凭据已缓存在浏览器 localStorage。</p>
        <NButton @click="clearAuth">清除凭据并重新登录</NButton>
      </div>

      <NDivider />

      <div>
        <h3 style="margin: 0 0 8px;">GitHub Actions Secrets 配置</h3>
        <NAlert type="info" :show-icon="true" style="margin-bottom: 12px;">
          在仓库 <strong>Settings → Secrets and variables → Actions</strong> 中添加以下 Secrets
        </NAlert>
        <NCode :code="secretsExample" language="bash" />
      </div>

      <NDivider />

      <div>
        <h3 style="margin: 0 0 8px;">触发注册</h3>
        <NAlert type="info" :show-icon="true" style="margin-bottom: 12px;">
          推送代码会自动触发注册流程；也可在 Actions 页面手动运行 workflow
        </NAlert>
        <NCode :code="workflowExample" language="bash" />
      </div>

      <NDivider />

      <div>
        <h3 style="margin: 0 0 8px;">安全提示</h3>
        <ul style="margin: 0; padding-left: 20px; color: #999;">
          <li>当前部署采用 HTTP（无 HTTPS），cookie/sessionid 在网络中明文传输</li>
          <li>建议在生产环境加上反向代理（nginx）+ Let's Encrypt 证书</li>
          <li>WEBHOOK_SECRET 请使用 32 字符以上的随机字符串</li>
          <li>admin 密码在首次启动时会自动生成并打印到 stderr</li>
        </ul>
      </div>
    </NSpace>
  </NCard>
</template>
