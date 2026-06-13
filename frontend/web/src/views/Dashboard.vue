<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { NCard, NGrid, NGridItem, NStatistic, NProgress, NDataTable, NTag, NEmpty, NSpin } from 'naive-ui'
import { useAccountsStore } from '@/stores/accounts'
import * as echarts from 'echarts'
import type { Account } from '@/api'

const store = useAccountsStore()
const trendChart = ref<HTMLDivElement | null>(null)
const failChart = ref<HTMLDivElement | null>(null)
let trendInstance: echarts.ECharts | null = null
let failInstance: echarts.ECharts | null = null

onMounted(async () => {
  await store.fetchStats()
  renderTrend()
  renderFailures()
})

watch(() => store.stats, () => {
  renderTrend()
  renderFailures()
}, { deep: true })

function renderTrend() {
  if (!trendChart.value || !store.stats) return
  if (!trendInstance) trendInstance = echarts.init(trendChart.value)
  const data = store.stats.daily_trend
  trendInstance.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['成功', '失败'], textStyle: { color: '#ccc' } },
    grid: { left: 40, right: 20, top: 30, bottom: 30 },
    xAxis: { type: 'category', data: data.map(d => d.date.slice(5)) },
    yAxis: { type: 'value' },
    series: [
      { name: '成功', type: 'bar', stack: 'total', data: data.map(d => d.success), itemStyle: { color: '#18a058' } },
      { name: '失败', type: 'bar', stack: 'total', data: data.map(d => d.failed), itemStyle: { color: '#d03050' } },
    ],
  })
}

function renderFailures() {
  if (!failChart.value || !store.stats) return
  if (!failInstance) failInstance = echarts.init(failChart.value)
  const data = store.stats.failure_reasons.slice(0, 8)
  failInstance.setOption({
    tooltip: { trigger: 'item' },
    grid: { left: 200, right: 20, top: 20, bottom: 20 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: data.map(d => d.reason.slice(0, 30)).reverse() },
    series: [{ type: 'bar', data: data.map(d => d.count).reverse(), itemStyle: { color: '#f0a020' } }],
  })
}
</script>

<template>
  <div>
    <NSpin :show="store.loading && !store.stats">
      <NGrid :cols="4" :x-gap="16" :y-gap="16" v-if="store.stats">
        <NGridItem>
          <NCard>
            <NStatistic label="总账号数" :value="store.stats.total" />
          </NCard>
        </NGridItem>
        <NGridItem>
          <NCard>
            <NStatistic label="成功注册" :value="store.stats.success">
              <template #suffix>
                <NTag type="success" size="small" style="margin-left: 8px;">{{ (store.stats.success_rate * 100).toFixed(1) }}%</NTag>
              </template>
            </NStatistic>
          </NCard>
        </NGridItem>
        <NGridItem>
          <NCard>
            <NStatistic label="失败数" :value="store.stats.failed" />
          </NCard>
        </NGridItem>
        <NGridItem>
          <NCard>
            <NStatistic label="近 24 小时" :value="store.stats.last_24h_success" />
            <template #footer>
              <span style="font-size: 12px; color: #999;">/{{ store.stats.last_24h_total }} 个</span>
            </template>
          </NCard>
        </NGridItem>
      </NGrid>

      <NGrid :cols="2" :x-gap="16" :y-gap="16" style="margin-top: 16px;" v-if="store.stats">
        <NGridItem>
          <NCard title="注册趋势（14 天）">
            <div ref="trendChart" style="height: 300px;"></div>
          </NCard>
        </NGridItem>
        <NGridItem>
          <NCard title="失败原因 Top 8">
            <div ref="failChart" style="height: 300px;"></div>
          </NCard>
        </NGridItem>
      </NGrid>

      <NEmpty v-if="store.stats && store.stats.total === 0" description="暂无账号数据，等待后端推送" style="margin-top: 60px;" />
    </NSpin>
  </div>
</template>
