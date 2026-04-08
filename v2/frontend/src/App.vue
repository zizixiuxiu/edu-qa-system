<template>
  <router-view />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAppStore } from './stores/app'

const appStore = useAppStore()

onMounted(() => {
  appStore.loadExperimentConfig()
})
</script>

<style>
/* 全局样式在 memphis.scss 中定义 */
</style>
