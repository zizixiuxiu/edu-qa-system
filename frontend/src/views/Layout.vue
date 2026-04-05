<template>
  <div class="app-container">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <!-- Logo -->
      <div class="logo-container">
        <div class="logo-shape"></div>
        <div class="logo-text">
          <span style="color: #FF78A5">E</span>
          <span style="color: #4CC9BB">D</span>
          <span style="color: #111">U</span>
        </div>
      </div>

      <!-- 导航菜单 -->
      <nav class="nav-menu">
        <router-link
          v-for="route in menuRoutes"
          :key="route.path"
          :to="route.path.startsWith('/') ? route.path : '/' + route.path"
          :class="['nav-item', { active: $route.path === (route.path.startsWith('/') ? route.path : '/' + route.path) }]"
        >
          <el-icon size="20">
            <component :is="route.meta?.icon" />
          </el-icon>
          <span>{{ route.meta?.title }}</span>
        </router-link>
      </nav>

      <!-- 实验模式显示 -->
      <div class="experiment-badge">
        <div class="badge-label">当前实验模式</div>
        <div class="badge-value">{{ appStore.experimentModeLabel }}</div>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="main-content">
      <div class="content-wrapper">
        <router-view />
      </div>
    </main>

    <!-- 装饰元素 -->
    <svg class="decor decor-1" width="120" height="120" viewBox="0 0 120 120" fill="none">
      <path d="M60 10 L110 90 L10 90 Z" fill="#FFF14F" stroke="#111" stroke-width="4"/>
    </svg>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAppStore } from '../stores/app'
import router from '../router'

const appStore = useAppStore()

const menuRoutes = computed(() => {
  return router.getRoutes()
    .find(r => r.name === 'Layout')?.children || []
})
</script>

<style scoped lang="scss">
.app-container {
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 24px;
  padding: 24px 32px;
  min-height: 100vh;
  position: relative;
  z-index: 10;
}

/* 默认窗口比例 - 类似图片中的宽屏布局 */
@media (min-width: 1400px) {
  .app-container {
    grid-template-columns: 280px 1fr;
    gap: 32px;
    padding: 32px 48px;
  }
}

/* 超宽屏优化 */
@media (min-width: 1920px) {
  .app-container {
    max-width: 1800px;
    grid-template-columns: 300px 1fr;
    gap: 40px;
    padding: 40px 64px;
  }
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.logo-container {
  background: var(--memphis-white);
  border: var(--border);
  box-shadow: var(--shadow);
  padding: 14px 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  transform: rotate(-2deg);
  transition: transform 0.2s ease;
  justify-content: center;
}

@media (min-width: 1400px) {
  .logo-container {
    padding: 16px;
    gap: 12px;
  }
}
.logo-container:hover {
  transform: rotate(0deg);
}

.logo-shape {
  width: 42px;
  height: 42px;
  background: var(--memphis-yellow);
  border: var(--border);
  border-radius: 50%;
  position: relative;
  background-image: var(--pattern-stipple);
  flex-shrink: 0;
}

@media (min-width: 1400px) {
  .logo-shape {
    width: 48px;
    height: 48px;
  }
}

.logo-text {
  font-family: var(--font-display);
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -1px;
  white-space: nowrap;
}

@media (min-width: 1400px) {
  .logo-text {
    font-size: 32px;
  }
}

.nav-menu {
  background: var(--memphis-white);
  border: var(--border);
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 14px;
  color: var(--memphis-black);
  text-decoration: none;
  border-bottom: 2px solid #eee;
  transition: all 0.15s ease;
}

@media (min-width: 1400px) {
  .nav-item {
    gap: 12px;
    padding: 16px 20px;
    font-size: 15px;
  }
}
.nav-item:hover {
  background: var(--memphis-yellow);
  padding-left: 24px;
}

@media (min-width: 1400px) {
  .nav-item:hover {
    padding-left: 28px;
  }
}
.nav-item.active {
  background: var(--memphis-pink);
  color: var(--memphis-white);
}
.nav-item:last-child {
  border-bottom: none;
}

.experiment-badge {
  background: var(--memphis-teal);
  border: var(--border);
  box-shadow: var(--shadow);
  padding: 14px 16px;
  margin-top: auto;
}

@media (min-width: 1400px) {
  .experiment-badge {
    padding: 16px;
  }
}
.badge-label {
  font-family: var(--font-display);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  opacity: 0.7;
  margin-bottom: 4px;
}
.badge-value {
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 700;
}

@media (min-width: 1400px) {
  .badge-value {
    font-size: 16px;
  }
}

.main-content {
  background: var(--memphis-white);
  border: var(--border);
  box-shadow: var(--shadow);
  min-height: calc(100vh - 48px);
  height: calc(100vh - 48px);
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

@media (min-width: 1400px) {
  .main-content {
    min-height: calc(100vh - 64px);
    height: calc(100vh - 64px);
  }
}

.content-wrapper {
  padding: 16px;
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

@media (min-width: 1400px) {
  .content-wrapper {
    padding: 20px;
  }
}

@media (min-width: 1920px) {
  .content-wrapper {
    padding: 24px;
  }
}

.content-wrapper > * {
  flex: 1;
  min-height: 0;
}

.decor {
  position: fixed;
  z-index: 0;
  pointer-events: none;
}
.decor-1 { top: 3%; right: 3%; transform: rotate(15deg); }

@media (max-width: 1024px) {
  .app-container {
    grid-template-columns: 1fr;
    padding: 16px;
  }
  .sidebar {
    display: none;
  }
}
</style>
