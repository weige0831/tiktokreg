<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import {
  NCard, NDataTable, NButton, NSpace, NInput, NTag, NPopconfirm, useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { RouterLink, useRouter } from 'vue-router'
import { api, type Account } from '@/api'

const message = useMessage()
const router = useRouter()
const loading = ref(false)
const data = ref<Account[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const statusFilter = ref<string | null>(null)
const searchQuery = ref('')

async function fetchData() {
  loading.value = true
  try {
    const r = await api.getAccounts({
      page: page.value,
      per_page: pageSize.value,
      status: statusFilter.value || undefined,
      search: searchQuery.value || undefined,
    })
    data.value = r.items
    total.value = r.total
  } catch (e: any) {
    message.error(`加载失败: ${e.message || e}`)
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)

function statusType(s: string) {
  return s === 'success' ? 'success' : 'error'
}

const columns: DataTableColumns<Account> = [
  { title: 'ID', key: 'id', width: 70 },
  {
    title: '邮箱',
    key: 'email',
    render: (row) =>
      h(RouterLink, { to: `/accounts/${row.id}`, style: 'color: #63e2b7;' }, { default: () => row.email }),
  },
  { title: '用户名', key: 'username', width: 150 },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row) => h(NTag, { type: statusType(row.status) }, { default: () => row.status === 'success' ? '成功' : '失败' }),
  },
  { title: '注册时间', key: 'created_at', width: 180, render: (row) => row.created_at?.replace('T', ' ').slice(0, 19) || '-' },
  { title: '代理', key: 'proxy_used', width: 150, render: (row) => row.proxy_used || '本机' },
  { title: '错误', key: 'error_msg', ellipsis: { tooltip: true }, render: (row) => row.error_msg?.slice(0, 60) || '-' },
  {
    title: '操作',
    key: 'actions',
    width: 180,
    render: (row) =>
      h(NSpace, { size: 'small' }, {
        default: () => [
          h(NButton, { size: 'small', onClick: () => router.push(`/accounts/${row.id}`) }, { default: () => '详情' }),
          h(NPopconfirm, {
            onPositiveClick: async () => {
              await api.deleteAccount(row.id)
              message.success('已删除')
              fetchData()
            },
          }, {
            trigger: () => h(NButton, { size: 'small', type: 'error' }, { default: () => '删除' }),
            default: () => '确认删除该账号？',
          }),
        ],
      }),
  },
]

function handlePageChange(p: number) {
  page.value = p
  fetchData()
}

function applyFilter() {
  page.value = 1
  fetchData()
}

async function exportJson() {
  try {
    await api.downloadExport(api.exportUrls.json(statusFilter.value || undefined), 'tiktok-accounts.json')
    message.success('导出成功')
  } catch (e: any) {
    message.error(`导出失败: ${e.message || e}`)
  }
}

async function exportCsv() {
  try {
    await api.downloadExport(api.exportUrls.csv(statusFilter.value || undefined), 'tiktok-accounts.csv')
    message.success('导出成功')
  } catch (e: any) {
    message.error(`导出失败: ${e.message || e}`)
  }
}
</script>

<template>
  <NCard>
    <template #header>
      <NSpace justify="space-between" align="center">
        <span>账号列表 ({{ total }})</span>
        <NSpace>
          <NButton @click="exportJson" size="small">导出 JSON</NButton>
          <NButton @click="exportCsv" size="small">导出 CSV</NButton>
        </NSpace>
      </NSpace>
    </template>

    <NSpace style="margin-bottom: 16px;">
      <NInput
        v-model:value="searchQuery"
        placeholder="搜索邮箱/用户名"
        style="width: 240px;"
        clearable
        @update:value="applyFilter"
      />
      <NButton
        v-for="s in [null, 'success', 'failed']"
        :key="s || 'all'"
        :type="statusFilter === s ? 'primary' : 'default'"
        size="small"
        @click="statusFilter = s; applyFilter()"
      >
        {{ s === null ? '全部' : s === 'success' ? '成功' : '失败' }}
      </NButton>
    </NSpace>

    <NDataTable
      :columns="columns"
      :data="data"
      :loading="loading"
      :pagination="{
        page,
        pageSize,
        itemCount: total,
        onChange: handlePageChange,
        showSizePicker: false,
      }"
      :bordered="false"
      :single-line="false"
      size="small"
    />
  </NCard>
</template>
