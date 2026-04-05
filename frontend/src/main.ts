import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'
import 'katex/dist/katex.min.css'

import App from './App.vue'
import router from './router'

// 孟菲斯风格自定义样式
import './styles/memphis.scss'

// KaTeX数学公式渲染
import katex from 'katex'

const app = createApp(App)

// 全局LaTeX渲染函数
const renderLatex = (text: string): string => {
  if (!text) return ''
  // 匹配 $...$ 和 $$...$$ 格式的LaTeX
  return text.replace(/\$\$(.+?)\$\$/g, (match, latex) => {
    try {
      return katex.renderToString(latex, { throwOnError: false, displayMode: true })
    } catch {
      return match
    }
  }).replace(/\$(.+?)\$/g, (match, latex) => {
    try {
      return katex.renderToString(latex, { throwOnError: false, displayMode: false })
    } catch {
      return match
    }
  })
}

// 注册全局属性
app.config.globalProperties.$renderLatex = renderLatex

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus)

app.mount('#app')
