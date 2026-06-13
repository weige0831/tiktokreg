<script setup lang="ts">
import { NConfigProvider, NMessageProvider, NDialogProvider, NLayout, NLayoutHeader, NMenu, darkTheme, zhCN, dateZhCN } from 'naive-ui'
import { h, type Component } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import type { MenuOption } from 'naive-ui'

const route = useRoute()

function renderLink(to: string, label: string): Component {
  return () => h(RouterLink, { to }, { default: () => label })
}

const menuOptions: MenuOption[] = [
  { label: renderLink('/dashboard', '仪表盘'), key: 'dashboard' },
  { label: renderLink('/accounts', '账号列表'), key: 'accounts' },
  { label: renderLink('/settings', '设置'), key: 'settings' },
]

function activeKey(): string {
  if (route.path.startsWith('/accounts')) return 'accounts'
  if (route.path.startsWith('/dashboard')) return 'dashboard'
  if (route.path.startsWith('/settings')) return 'settings'
  return ''
}
</script>

<template>
  <NConfigProvider :theme="darkTheme" :locale="zhCN" :date-locale="dateZhCN">
    <NMessageProvider>
      <NDialogProvider>
        <NLayout position="absolute">
          <NLayoutHeader bordered style="height: 56px; display: flex; align-items: center; padding: 0 24px;">
            <div style="font-weight: 600; font-size: 16px; margin-right: 32px;">
              🎵 TikTok Registrar
            </div>
            <NMenu mode="horizontal" :options="menuOptions" :value="activeKey()" />
          </NLayoutHeader>
          <NLayout :native-scrollbar="false" style="height: calc(100vh - 56px); padding: 24px;">
            <RouterView />
          </NLayout>
        </NLayout>
      </NDialogProvider>
    </NMessageProvider>
  </NConfigProvider>
</template>

<style>
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
* { box-sizing: border-box; }
</style>
