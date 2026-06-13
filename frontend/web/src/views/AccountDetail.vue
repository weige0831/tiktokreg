<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NCard, NSpace, NButton, NDescriptions, NDescriptionsItem, NTag, NSpin, NCollapse, NCollapseItem, NCode, useMessage,
} from 'naive-ui'
import { api, type AccountDetail } from '@/api'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const account = ref<AccountDetail | null>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const id = Number(route.params.id)
    account.value = await api.getAccount(id)
  } catch (e: any) {
    message.error(`加载失败: ${e.message || e}`)
  } finally {
    loading.value = false
  }
})

function formatCookies(cookiesJson: string | null): string {
  if (!cookiesJson) return '[]'
  try {
    return JSON.stringify(JSON.parse(cookiesJson), null, 2)
  } catch {
    return cookiesJson
  }
}

async function exportCookies() {
  if (!account.value) return
  await api.downloadExport(api.exportUrls.accountCookies(account.value.id), `cookies-${account.value.email}.txt`)
}

async function exportJson() {
  if (!account.value) return
  await api.downloadExport(api.exportUrls.accountInfo(account.value.id), `info-${account.value.email}.json`)
}

async function markChecked() {
  if (!account.value) return
  await api.markChecked(account.value.id)
  message.success('已标记')
}

async function copySession() {
  if (!account.value?.session_id) return
  await navigator.clipboard.writeText(account.value.session_id)
  message.success('sessionid 已复制')
}
</script>

<template>
  <NSpin :show="loading">
    <NCard v-if="account">
      <template #header>
        <NSpace justify="space-between" align="center">
          <span>{{ account.email }}</span>
          <NSpace>
            <NButton size="small" @click="markChecked">标记已检查</NButton>
            <NButton size="small" @click="exportCookies">导出 cookies.txt</NButton>
            <NButton size="small" @click="exportJson">导出 info.json</NButton>
            <NButton size="small" @click="router.push('/accounts')">返回列表</NButton>
          </NSpace>
        </NSpace>
      </template>

      <NDescriptions :column="2" bordered size="small">
        <NDescriptionsItem label="ID">{{ account.id }}</NDescriptionsItem>
        <NDescriptionsItem label="状态">
          <NTag :type="account.status === 'success' ? 'success' : 'error'">
            {{ account.status === 'success' ? '成功' : '失败' }}
          </NTag>
        </NDescriptionsItem>
        <NDescriptionsItem label="邮箱">{{ account.email }}</NDescriptionsItem>
        <NDescriptionsItem label="用户名">{{ account.username || '-' }}</NDescriptionsItem>
        <NDescriptionsItem label="密码">
          <code>{{ account.password }}</code>
        </NDescriptionsItem>
        <NDescriptionsItem label="生日">{{ account.birth_date || '-' }}</NDescriptionsItem>
        <NDescriptionsItem label="注册时间">{{ account.registered_at?.replace('T', ' ').slice(0, 19) }}</NDescriptionsItem>
        <NDescriptionsItem label="批次 ID">{{ account.batch_id || '-' }}</NDescriptionsItem>
        <NDescriptionsItem label="代理">{{ account.proxy_used || '本机' }}</NDescriptionsItem>
        <NDescriptionsItem label="指纹 Hash"><code>{{ account.fingerprint_hash }}</code></NDescriptionsItem>
        <NDescriptionsItem label="时区">{{ account.timezone || '-' }}</NDescriptionsItem>
        <NDescriptionsItem label="语言">{{ account.locale || '-' }}</NDescriptionsItem>
        <NDescriptionsItem label="User-Agent" :span="2"><code style="word-break: break-all;">{{ account.user_agent }}</code></NDescriptionsItem>
        <NDescriptionsItem label="错误信息" :span="2" v-if="account.error_msg">
          <code style="color: #d03050;">{{ account.error_msg }}</code>
        </NDescriptionsItem>
      </NDescriptions>

      <NCollapse style="margin-top: 16px;">
        <NCollapseItem title="核心凭证（点击复制 sessionid）" name="credentials">
          <NSpace vertical>
            <NDescriptions :column="1" bordered size="small" label-placement="left">
              <NDescriptionsItem label="sessionid">
                <NSpace>
                  <code style="word-break: break-all;">{{ account.session_id || '-' }}</code>
                  <NButton size="tiny" @click="copySession" v-if="account.session_id">复制</NButton>
                </NSpace>
              </NDescriptionsItem>
              <NDescriptionsItem label="msToken"><code style="word-break: break-all;">{{ account.ms_token || '-' }}</code></NDescriptionsItem>
              <NDescriptionsItem label="tt-target-idc"><code>{{ account.tt_target_idc || '-' }}</code></NDescriptionsItem>
            </NDescriptions>
          </NSpace>
        </NCollapseItem>

        <NCollapseItem title="重要 Cookie 列表" name="important">
          <NCode :code="JSON.stringify(account.important_cookies || {}, null, 2)" language="json" />
        </NCollapseItem>

        <NCollapseItem title="完整 Cookie (Playwright JSON)" name="cookies">
          <NCode :code="formatCookies(account.cookies_json)" language="json" />
        </NCollapseItem>
      </NCollapse>
    </NCard>
  </NSpin>
</template>
