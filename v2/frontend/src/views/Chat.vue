<template>
  <div class="chat-page">
    <div class="chat-container">
      <!-- 顶部装饰条 -->
      <div class="chat-header-decor">
        <div class="window-dot pink"></div>
        <div class="window-dot yellow"></div>
        <div class="window-dot teal"></div>
        <span class="header-title">智能问答 Expert Chat</span>
      </div>

      <!-- 消息区域 -->
      <div class="chat-messages" ref="messagesContainer">
        <div v-if="messages.length === 0" class="welcome-message">
          <h2>👋 欢迎使用 EduQA 教育系统</h2>
          <p>我可以帮助你解答 K12 教育领域的各类问题</p>
          <div class="quick-questions">
            <el-tag 
              v-for="q in quickQuestions" 
              :key="q"
              class="quick-tag"
              effect="light"
              @click="setQuestion(q)"
            >
              {{ q }}
            </el-tag>
          </div>
        </div>

        <div
          v-for="(msg, index) in messages"
          :key="index"
          :class="['message', msg.role]"
        >
          <div class="message-sender">
            {{ msg.role === 'user' ? '你' : msg.expert_name || 'AI专家' }}
          </div>
          <div class="message-content">
            <div v-if="msg.image" class="message-image">
              <img :src="msg.image" alt="uploaded" />
            </div>
            <div class="message-text markdown-content" v-html="renderMarkdown(msg.content)"></div>
            
            <!-- 引用知识 -->
            <div v-if="msg.knowledges?.length" class="knowledges">
              <el-collapse>
                <el-collapse-item>
                  <template #title>
                    📚 引用的知识点 ({{ msg.knowledges.length }}条)
                    <el-tag v-if="msg.tier_info" size="small" type="success" effect="light" style="margin-left: 8px;">
                      {{ msg.tier_info }}
                    </el-tag>
                  </template>
                  <div 
                    v-for="(k, i) in msg.knowledges" 
                    :key="i"
                    class="knowledge-item"
                    :class="{ 'tier-1': k.tier === 1, 'tier-2': k.tier === 2, 'tier-local': k.tier === 0 }"
                  >
                    <div class="knowledge-header">
                      <el-tag size="small" :type="k.tier === 1 ? 'primary' : k.tier === 2 ? 'info' : 'success'" effect="light">
                        {{ k.tier === 1 ? '学科库' : k.tier === 2 ? '通用库' : '本地' }}
                      </el-tag>
                      <span class="knowledge-source">{{ k.source }}</span>
                      <span class="knowledge-score">{{ (k.score * 100).toFixed(1) }}%</span>
                    </div>
                    <div class="knowledge-content">{{ k.content }}</div>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>

            <!-- 元信息 -->
            <div v-if="msg.metadata" class="message-meta">
              <el-tag size="small" type="info" effect="light">
                ⏱️ {{ msg.metadata.response_time?.toFixed(0) }}ms
              </el-tag>
              <el-tag size="small" type="success" effect="light">
                🎯 {{ msg.metadata.expert_subject }}
              </el-tag>
            </div>
          </div>
        </div>

        <!-- 加载中 -->
        <div v-if="isLoading" class="message ai loading">
          <div class="message-sender">AI专家</div>
          <div class="message-content">
            <el-icon class="loading-icon" :size="24"><Loading /></el-icon>
            正在思考中...
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="chat-input-area">
        <div class="input-wrapper">
          <!-- 工具栏 -->
          <div class="input-tools">
            <el-upload
              accept="image/*"
              :show-file-list="false"
              :before-upload="handleImageUpload"
            >
              <el-button type="info" text>
                <el-icon><Picture /></el-icon>
                上传图片
              </el-button>
            </el-upload>
            <span v-if="currentImage" class="image-hint">
              已选择图片 ✓
            </span>
          </div>

          <!-- 输入框 -->
          <el-input
            v-model="inputMessage"
            type="textarea"
            :rows="3"
            placeholder="请输入你的问题..."
            @keydown.enter.prevent="sendMessage"
          />
        </div>

        <!-- 发送按钮 -->
        <button 
          class="send-btn"
          @click="sendMessage"
          :disabled="isLoading || (!inputMessage.trim() && !currentImage)"
        >
          <el-icon size="24"><Promotion /></el-icon>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { chatApi } from '../api'
import katex from 'katex'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'

// 配置 marked
marked.setOptions({
  breaks: true,
  gfm: true
})

// 代码高亮函数
const highlightCode = (code: string, language?: string): string => {
  if (language && hljs.getLanguage(language)) {
    try {
      return hljs.highlight(code, { language }).value
    } catch {
      return hljs.highlightAuto(code).value
    }
  }
  return hljs.highlightAuto(code).value
}

// 渲染 Markdown + LaTeX
const renderMarkdown = (text: string): string => {
  if (!text) return ''
  
  // 复制文本进行处理
  let processedText = text
  
  // 创建占位符映射
  const placeholders = new Map<string, string>()
  let placeholderIndex = 0
  
  const addPlaceholder = (content: string): string => {
    // 使用 HTML 注释格式，避免被 marked 解析
    const key = `<!--PLACEHOLDER_${placeholderIndex++}-->`
    placeholders.set(key, content)
    return key
  }
  
  // 1. 保护代码块
  processedText = processedText.replace(/```(\w+)?\n([\s\S]*?)```/g, (_, lang, code) => {
    const highlighted = highlightCode(code.trim(), lang)
    const wrapped = `<pre class="code-block"><code class="hljs ${lang || ''}">${highlighted}</code></pre>`
    return addPlaceholder(wrapped)
  })
  
  // 2. 保护 LaTeX 公式（块级）
  processedText = processedText.replace(/\$\$([\s\S]+?)\$\$/g, (_, latex) => {
    try {
      const rendered = katex.renderToString(latex.trim(), { 
        throwOnError: false, 
        displayMode: true 
      })
      return addPlaceholder(rendered)
    } catch {
      return addPlaceholder(`$$${latex}$$`)
    }
  })
  
  // 3. 保护 LaTeX 公式（行内）
  processedText = processedText.replace(/\$([^$\n]+?)\$/g, (_, latex) => {
    try {
      const rendered = katex.renderToString(latex.trim(), { 
        throwOnError: false, 
        displayMode: false 
      })
      return addPlaceholder(rendered)
    } catch {
      return addPlaceholder(`$${latex}$`)
    }
  })
  
  // 4. 使用 marked 渲染 Markdown
  const html = marked.parse(processedText, { 
    async: false,
    breaks: true,
    gfm: true 
  }) as string
  
  // 5. 恢复所有占位符（使用 replaceAll 确保全部替换）
  let result = html
  placeholders.forEach((value, key) => {
    result = result.replaceAll(key, value)
  })
  
  // 6. 处理行内代码（marked 生成的）
  result = result.replace(/<code>([^<]+)<\/code>/g, (match, code) => {
    // 检查是否已经被高亮
    if (code.includes('class="hljs"') || code.includes('hljs-')) {
      return match
    }
    return `<code class="inline-code">${code}</code>`
  })
  
  return result
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  image?: string
  expert_name?: string
  knowledges?: any[]
  tier_info?: string
  metadata?: any
}

const messages = ref<Message[]>([])
const inputMessage = ref('')
const currentImage = ref('')
const isLoading = ref(false)
const messagesContainer = ref<HTMLElement>()

const quickQuestions = [
  '解方程: 2x + 5 = 13',
  '什么是牛顿第二定律？',
  '请解释光合作用',
  '如何写好议论文？'
]

function setQuestion(q: string) {
  inputMessage.value = q
}

async function handleImageUpload(file: File) {
  try {
    const res: any = await chatApi.uploadImage(file)
    if (res.code === 200) {
      currentImage.value = res.data.base64
      ElMessage.success('图片上传成功')
    }
  } catch (error) {
    ElMessage.error('图片上传失败')
  }
  return false // 阻止默认上传
}

async function sendMessage() {
  // 允许纯文字、纯图片、或图文混合
  const hasText = inputMessage.value.trim()
  const hasImage = currentImage.value
  
  if ((!hasText && !hasImage) || isLoading.value) return

  const userMsg: Message = {
    role: 'user',
    content: inputMessage.value || '[图片]',
    image: currentImage.value || undefined
  }
  messages.value.push(userMsg)

  const question = inputMessage.value || '请解答图片中的题目'
  const image = currentImage.value
  
  inputMessage.value = ''
  currentImage.value = ''
  isLoading.value = true

  scrollToBottom()

  try {
    const res: any = await chatApi.send({
      query: question,
      image: image || undefined
    })

    if (res.code === 200) {
      // 计算知识来源统计
      const knowledges = res.data.used_knowledges || []
      const tier1Count = knowledges.filter((k: any) => k.tier === 1).length
      const tier2Count = knowledges.filter((k: any) => k.tier === 2).length
      const localCount = knowledges.filter((k: any) => k.tier === 0).length
      let tierInfo = ''
      if (localCount > 0) tierInfo += `本地${localCount} `
      if (tier1Count > 0) tierInfo += `学科${tier1Count} `
      if (tier2Count > 0) tierInfo += `通用${tier2Count}`
      
      messages.value.push({
        role: 'assistant',
        content: res.data.answer,
        expert_name: res.data.expert_name,
        knowledges: knowledges,
        tier_info: tierInfo.trim(),
        metadata: {
          response_time: res.data.response_time,
          expert_subject: res.data.expert_subject
        }
      })
    } else {
      ElMessage.error(res.message || '请求失败')
    }
  } catch (error) {
    ElMessage.error('网络错误')
  } finally {
    isLoading.value = false
    scrollToBottom()
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}
</script>

<style scoped lang="scss">
.chat-page {
  height: calc(100vh - 110px);
}

@media (min-width: 1400px) {
  .chat-page {
    height: calc(100vh - 140px);
  }
}

.chat-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  border: var(--border);
  box-shadow: var(--shadow);
  background: var(--memphis-white);
}

.chat-header-decor {
  height: 36px;
  background: var(--memphis-yellow);
  background-image: var(--pattern-stipple);
  border-bottom: var(--border);
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 8px;
}
.window-dot {
  width: 14px;
  height: 14px;
  border: 2px solid var(--memphis-black);
  border-radius: 50%;
}
.window-dot.pink { background: var(--memphis-pink); }
.window-dot.yellow { background: var(--memphis-yellow); }
.window-dot.teal { background: var(--memphis-teal); }
.header-title {
  margin-left: auto;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 13px;
  text-transform: uppercase;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #fafafa;
  background-image: 
    linear-gradient(to right, #e0e0e0 1px, transparent 1px),
    linear-gradient(to bottom, #e0e0e0 1px, transparent 1px);
  background-size: 40px 40px;
}

@media (min-width: 768px) {
  .chat-messages {
    padding: 24px;
  }
}

@media (min-width: 1400px) {
  .chat-messages {
    padding: 32px;
  }
}

.welcome-message {
  text-align: center;
  padding: 40px 16px;
}

/* 响应式标题 - 自适应变化 */
.welcome-message h2 {
  font-family: var(--font-display);
  font-size: clamp(20px, 4vw, 32px);
  margin-bottom: 12px;
  line-height: 1.3;
  word-wrap: break-word;
}

.welcome-message p {
  color: #666;
  margin-bottom: 24px;
  font-size: clamp(13px, 2vw, 16px);
  line-height: 1.5;
}

@media (min-width: 768px) {
  .welcome-message {
    padding: 50px 24px;
  }
  .welcome-message p {
    margin-bottom: 28px;
  }
}

@media (min-width: 1400px) {
  .welcome-message {
    padding: 60px 32px;
  }
  .welcome-message p {
    margin-bottom: 32px;
  }
}
.quick-questions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  max-width: 800px;
  margin: 0 auto;
}

@media (min-width: 768px) {
  .quick-questions {
    gap: 10px;
  }
}

@media (min-width: 1400px) {
  .quick-questions {
    gap: 12px;
  }
}
.quick-tag {
  cursor: pointer;
  transition: all 0.2s;
}
.quick-tag:hover {
  transform: scale(1.05);
}

.message {
  max-width: 85%;
  margin-bottom: 24px;
}
.message.user {
  margin-left: auto;
}
.message.ai {
  margin-right: auto;
}

.message-sender {
  font-family: var(--font-display);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  padding: 4px 12px;
  border: var(--border);
  background: var(--memphis-white);
  box-shadow: 2px 2px 0 0 var(--memphis-black);
  display: inline-block;
  margin-bottom: -12px;
  position: relative;
  z-index: 2;
}
.message.user .message-sender {
  background: var(--memphis-pink);
  margin-left: auto;
  display: block;
  width: fit-content;
}
.message.ai .message-sender {
  background: var(--memphis-teal);
}

.message-content {
  padding: 20px;
  border: var(--border);
  font-size: 15px;
  line-height: 1.7;
  position: relative;
  z-index: 1;
  background: var(--memphis-white);
  box-shadow: 4px 4px 0 0 var(--memphis-black);
}
.message.user .message-content {
  background: var(--memphis-yellow);
  border-radius: 20px 20px 0 20px;
}
.message.ai .message-content {
  border-radius: 20px 20px 20px 0;
}

.message-image img {
  max-width: 200px;
  max-height: 200px;
  border: var(--border);
  margin-bottom: 12px;
}

.knowledges {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 2px dashed #ddd;
}
.knowledge-item {
  padding: 12px;
  background: #f5f5f5;
  border-left: 4px solid var(--memphis-teal);
  margin-bottom: 8px;
  font-size: 13px;
}
.knowledge-item.tier-1 {
  border-left-color: #409eff;
  background: #ecf5ff;
}
.knowledge-item.tier-2 {
  border-left-color: #909399;
  background: #f4f4f5;
}
.knowledge-item.tier-local {
  border-left-color: #67c23a;
  background: #f0f9eb;
}
.knowledge-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}
.knowledge-source {
  color: #666;
  font-size: 12px;
}
.knowledge-score {
  margin-left: auto;
  color: #409eff;
  font-weight: 600;
  font-size: 12px;
}
.knowledge-content {
  color: #333;
  line-height: 1.5;
}

.message-meta {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #eee;
}

.loading-icon {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.chat-input-area {
  padding: 16px;
  background: var(--memphis-white);
  border-top: var(--border);
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

@media (min-width: 768px) {
  .chat-input-area {
    padding: 20px 24px;
    gap: 16px;
  }
}

.input-wrapper {
  flex: 1;
  border: var(--border);
  box-shadow: var(--shadow);
  background: var(--memphis-white);
}
.input-wrapper:focus-within {
  box-shadow: var(--shadow-hover);
}

.input-tools {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 2px solid #e0e0e0;
  gap: 12px;
}
.image-hint {
  font-size: 12px;
  color: var(--memphis-teal);
  font-weight: 600;
}

:deep(.el-textarea__inner) {
  border: none !important;
  box-shadow: none !important;
  font-family: var(--font-body);
  font-size: 15px;
  padding: 16px;
  resize: none;
}

.send-btn {
  width: 64px;
  height: 64px;
  background: var(--memphis-pink);
  border: var(--border);
  box-shadow: var(--shadow);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.1s;
  color: var(--memphis-black);
}
.send-btn:hover {
  background: var(--memphis-yellow);
  box-shadow: var(--shadow-hover);
  transform: translate(-2px, -2px);
}
.send-btn:active {
  box-shadow: var(--shadow-active);
  transform: translate(var(--shadow-size), var(--shadow-size));
}
.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Markdown 内容样式 */
.markdown-content {
  line-height: 1.7;
  
  /* 标题样式 */
  :deep(h1) {
    font-size: 1.5em;
    font-weight: 700;
    margin: 1em 0 0.5em;
    padding-bottom: 0.3em;
    border-bottom: 2px solid var(--memphis-black);
  }
  
  :deep(h2) {
    font-size: 1.3em;
    font-weight: 700;
    margin: 1em 0 0.5em;
    padding-bottom: 0.2em;
    border-bottom: 1px solid #ddd;
  }
  
  :deep(h3) {
    font-size: 1.1em;
    font-weight: 700;
    margin: 0.8em 0 0.4em;
  }
  
  /* 段落和列表 */
  :deep(p) {
    margin: 0.5em 0;
  }
  
  :deep(ul), :deep(ol) {
    margin: 0.5em 0;
    padding-left: 1.5em;
  }
  
  :deep(li) {
    margin: 0.3em 0;
  }
  
  /* 表格样式 */
  :deep(table) {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
    font-size: 0.95em;
    border: var(--border);
    box-shadow: 3px 3px 0 0 var(--memphis-black);
  }
  
  :deep(th) {
    background: var(--memphis-yellow);
    font-weight: 700;
    text-align: left;
    padding: 10px 12px;
    border: var(--border);
    font-family: var(--font-display);
  }
  
  :deep(td) {
    padding: 10px 12px;
    border: var(--border);
    border-width: 1px;
  }
  
  :deep(tr:nth-child(even)) {
    background: #f8f8f8;
  }
  
  :deep(tr:hover) {
    background: #f0f0f0;
  }
  
  /* 代码块样式 */
  :deep(.code-block) {
    margin: 1em 0;
    border: var(--border);
    border-radius: 0;
    box-shadow: 4px 4px 0 0 var(--memphis-black);
    overflow: hidden;
    background: #1e1e1e;
  }
  
  :deep(.code-block code) {
    display: block;
    padding: 16px;
    font-family: 'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 13px;
    line-height: 1.6;
    overflow-x: auto;
    background: #1e1e1e;
    color: #d4d4d4;
  }
  
  /* 行内代码样式 */
  :deep(.inline-code) {
    font-family: 'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 0.9em;
    background: #f0f0f0;
    padding: 2px 6px;
    border: 1px solid #ddd;
    border-radius: 3px;
    color: #d63384;
  }
  
  /* 引用块样式 */
  :deep(blockquote) {
    margin: 1em 0;
    padding: 12px 16px;
    border-left: 4px solid var(--memphis-pink);
    background: #f8f8f8;
    font-style: italic;
  }
  
  :deep(blockquote p) {
    margin: 0;
  }
  
  /* 链接样式 */
  :deep(a) {
    color: var(--memphis-blue);
    text-decoration: underline;
    text-underline-offset: 2px;
  }
  
  :deep(a:hover) {
    color: var(--memphis-pink);
  }
  
  /* 分隔线样式 - 灰色系 */
  :deep(hr) {
    border: none;
    height: 1px;
    background: linear-gradient(to right, transparent, #c0c0c0, #a0a0a0, #c0c0c0, transparent);
    margin: 1.5em 0;
    position: relative;
  }
  
  :deep(hr)::before {
    content: '◆';
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    background: var(--memphis-white);
    padding: 0 8px;
    color: #909090;
    font-size: 10px;
  }
  
  /* 强调样式 */
  :deep(strong) {
    font-weight: 700;
    color: var(--memphis-black);
  }
  
  :deep(em) {
    font-style: italic;
  }
  
  /* LaTeX公式样式 */
  :deep(.katex) {
    font-size: 1em;
  }
  
  :deep(.katex-display) {
    margin: 1em 0;
    overflow-x: auto;
    overflow-y: hidden;
  }
}

.message-text {
  word-wrap: break-word;
}
</style>
