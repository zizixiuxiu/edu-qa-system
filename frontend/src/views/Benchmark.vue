<template>
  <div class="benchmark-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-title">
        <el-icon size="28"><Trophy /></el-icon>
        <h1>GAOKAO-Bench 基准测试</h1>
      </div>
      <p class="header-desc">基于中国高考题的标准化评测框架，错题自动进入迭代优化</p>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-cards">
      <div class="stat-card blue">
        <div class="stat-icon">📚</div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.total_questions }}</div>
          <div class="stat-label">题目总数</div>
        </div>
      </div>
      <div class="stat-card green">
        <div class="stat-icon">✅</div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.correct_count }}</div>
          <div class="stat-label">正确数</div>
        </div>
      </div>
      <div class="stat-card red">
        <div class="stat-icon">❌</div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.wrong_count }}</div>
          <div class="stat-label">错误数</div>
        </div>
      </div>
      <div class="stat-card yellow">
        <div class="stat-icon">📊</div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.accuracy_rate }}%</div>
          <div class="stat-label">正确率</div>
        </div>
      </div>
      <div class="stat-card purple">
        <div class="stat-icon">⭐</div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.avg_score }}</div>
          <div class="stat-label">平均分</div>
        </div>
      </div>
    </div>

    <!-- 操作区域 -->
    <div class="action-section">
      <!-- 数据集导入 -->
      <div class="action-card">
        <h3>导入 GAOKAO-Bench 数据集</h3>
        
        <!-- 本地数据集状态 -->
        <div v-if="datasetInfo.exists" class="dataset-status">
          <el-alert type="success" :closable="false">
            <template #title>
              已检测到本地数据集
            </template>
            <div class="dataset-detail">
              <p>路径: {{ datasetInfo.path }}</p>
              <p>共 {{ datasetInfo.total_questions }} 道题目，{{ datasetInfo.total_files }} 个文件</p>
            </div>
          </el-alert>
          
          <div class="subject-tags">
            <span>学科分布:</span>
            <el-tag 
              v-for="file in datasetInfo.files" 
              :key="file.filename"
              class="subject-tag"
              :type="getSubjectTagType(file.subject_cn)"
              effect="light"
            >
              {{ file.subject_cn }} ({{ file.count }})
            </el-tag>
          </div>
          
          <div class="import-actions">
            <el-button 
              type="primary"
              @click="importLocalDataset"
              :loading="importing"
            >
              一键导入全部
            </el-button>
            <el-select v-model="selectedImportSubject" placeholder="选择学科导入" clearable class="subject-select">
              <el-option
                v-for="file in datasetInfo.files"
                :key="file.subject_en"
                :label="file.subject_cn + ' (' + file.count + '题)'"
                :value="file.subject_cn"
              />
            </el-select>
            <el-button 
              v-if="selectedImportSubject"
              type="primary"
              @click="importSubjectDataset"
              :loading="importing"
            >
              导入选中学科
            </el-button>
          </div>
        </div>
        
        <div v-else class="dataset-missing">
          <el-alert type="warning" :closable="false">
            <template #title>
              ⚠️ 未检测到本地数据集
            </template>
            <p>请配置 GAOKAO_BENCH_PATH 环境变量或手动指定路径</p>
          </el-alert>
          
          <div class="import-form">
            <el-input
              v-model="customDatasetPath"
              placeholder="输入本地数据集路径"
              class="path-input"
            />
            <el-button 
              type="primary"
              @click="checkLocalDataset"
            >
              检测路径
            </el-button>
          </div>
        </div>
      </div>

      <!-- 测试配置 -->
      <div class="action-card">
        <h3>配置测试</h3>
        <div class="test-config">
          <div class="config-row">
            <label>选择专家:</label>
            <el-select v-model="selectedExpert" class="config-select">
              <el-option :key="'auto'" label="自动路由 (按学科匹配)" value="auto" />
              <el-option
                v-for="expert in experts"
                :key="expert.id"
                :label="expert.name + ' (' + expert.subject + ')'"
                :value="expert.id"
              />
            </el-select>
            <el-tooltip content="自动路由会根据题目学科自动匹配合适的专家">
              <el-icon class="help-icon"><QuestionFilled /></el-icon>
            </el-tooltip>
          </div>
          
          <div class="config-row">
            <label>测试模式:</label>
            <el-radio-group v-model="testMode">
              <el-radio value="all">全部题目</el-radio>
              <el-radio value="random">随机100道</el-radio>
              <el-radio value="by_subject">按学科</el-radio>
            </el-radio-group>
          </div>
          
          <div v-if="testMode === 'by_subject'" class="config-row">
            <label>选择学科:</label>
            <el-select v-model="testSubject" placeholder="选择学科" clearable class="config-select">
              <el-option
                v-for="(count, subject) in stats.by_subject"
                :key="subject"
                :label="subject + ' (' + count + '题)'"
                :value="subject"
                :disabled="count === 0"
              />
            </el-select>
          </div>
          
          <div class="config-row">
            <label>选择年份:</label>
            <el-select v-model="testYear" placeholder="全部年份" clearable class="config-select">
              <el-option label="2010-2022 全部" value="" />
              <el-option label="2022" value="2022" />
              <el-option label="2021" value="2021" />
              <el-option label="2020" value="2020" />
              <el-option label="2019" value="2019" />
              <el-option label="2018" value="2018" />
            </el-select>
          </div>
          
          <el-button 
            type="success" 
            size="large"
            @click="startBenchmark"
            :loading="testing"
            :disabled="!canStartTest"
          >
            开始测试
          </el-button>
          
          <el-button 
            type="warning" 
            size="small"
            @click="resetBenchmark"
            v-if="testing"
          >
            重置状态
          </el-button>
          
          <!-- 调试信息 -->
          <div v-if="!canStartTest" class="debug-info">
            <el-alert type="info" :closable="false" size="small">
              <template #title>
                为什么禁用？
              </template>
              <div class="debug-items">
                <span :class="{ ok: stats.total_questions > 0 }">✓ 导入题目{{ stats.total_questions > 0 ? '' : '(未导入)' }}</span>
                <span :class="{ ok: !testing }">✓ 未在测试{{ !testing ? '' : '(测试中)' }}</span>
              </div>
            </el-alert>
          </div>
        </div>
      </div>
    </div>

    <!-- 测试监控面板 - 常驻显示 -->
    <div class="progress-section">
      <div class="progress-card" :class="{ 'idle': !testing && progress.total === 0, 'running': testing, 'completed': !testing && progress.total > 0 && progress.current >= progress.total }">
        <div class="progress-header">
          <span class="status-title">
            <el-icon v-if="testing" class="status-icon running"><Loading /></el-icon>
            <el-icon v-else-if="progress.total > 0 && progress.current >= progress.total" class="status-icon completed"><CircleCheck /></el-icon>
            <el-icon v-else class="status-icon idle"><VideoPause /></el-icon>
            {{ testing ? '测试进行中' : (progress.total > 0 && progress.current >= progress.total ? '测试已完成' : '测试监控') }}
          </span>
          <div class="progress-actions">
            <template v-if="testing">
              <span class="progress-count">{{ progress.current }}/{{ progress.total }}</span>
              <el-button 
                type="danger" 
                size="small" 
                @click="stopBenchmark"
                :loading="stopping"
                class="stop-btn"
              >
                <el-icon><CircleClose /></el-icon>
                停止
              </el-button>
            </template>
            <template v-else-if="progress.total > 0">
              <span class="progress-count">{{ progress.current }}/{{ progress.total }}</span>
              <el-tag :type="progress.current >= progress.total ? 'success' : 'info'" size="small" effect="light">
                {{ progress.current >= progress.total ? '已完成' : '已停止' }}
              </el-tag>
            </template>
            <template v-else>
              <el-tag type="info" size="small" effect="light">等待启动</el-tag>
            </template>
          </div>
        </div>
        
        <!-- 进度条 - 始终显示 -->
        <el-progress 
          :percentage="progressPercentage" 
          :stroke-width="20"
          :status="progressStatus"
          :show-text="progress.total > 0"
        />
        
        <!-- 详情信息 -->
        <div class="progress-detail">
          <template v-if="testing">
            <span class="latex-content" v-html="'当前: ' + renderLatex(progress.current_question || '准备中...')"></span>
            <span class="progress-time">{{ formatTime(progress.elapsed_time) }}</span>
          </template>
          <template v-else-if="progress.total > 0">
            <span class="status-desc">
              {{ progress.current >= progress.total 
                ? `测试完成！共完成 ${progress.current} 道题目` 
                : `测试已停止，已完成 ${progress.current}/${progress.total} 道题目` 
              }}
            </span>
            <span class="progress-time">用时: {{ formatTime(progress.elapsed_time) }}</span>
          </template>
          <template v-else>
            <span class="status-desc">暂无进行中的测试，点击"开始测试"启动新的评测</span>
            <span class="progress-time">--:--</span>
          </template>
        </div>
      </div>
      
      <!-- 实时完成的题目 - 只在有数据时显示 -->
      <div v-if="recentResults.length > 0" class="recent-results">
        <h4>
          <el-icon><List /></el-icon>
          最近完成 ({{ recentResults.length }}道)
        </h4>
        <el-table :data="recentResults.slice(0, 5)" size="small" class="recent-table" :show-header="false">
          <el-table-column width="35">
            <template #default="{ $index }">
              <span class="recent-index">{{ $index + 1 }}</span>
            </template>
          </el-table-column>
          <el-table-column width="80">
            <template #default="{ row }">
              <el-tag :type="row.is_correct ? 'success' : 'danger'" size="small" effect="light" class="result-tag">
                {{ row.is_correct ? '✓ 正确' : '✗ 错误' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column min-width="120">
            <template #default="{ row }">
              <span class="recent-question">{{ row.question?.substring(0, 45) }}{{ row.question?.length > 45 ? '...' : '' }}</span>
            </template>
          </el-table-column>
          <el-table-column width="50" align="right">
            <template #default="{ row }">
              <span class="recent-score" :class="getScoreClass(row.overall_score)">{{ row.overall_score?.toFixed(1) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
      
      <!-- 空状态提示 -->
      <div v-else class="recent-results empty">
        <el-empty description="暂无测试记录" :image-size="60">
          <template #description>
            <span class="empty-text">开始测试后将显示实时结果</span>
          </template>
        </el-empty>
      </div>
    </div>

    <!-- 详细评测报告 -->
    <div v-if="detailedReport.summary" class="detailed-report-section">
      <div class="report-header">
        <h3>📊 详细评测报告</h3>
        <div class="report-actions">
          <el-button type="info" size="small" @click="showReportManager = true" :icon="FolderOpenedIcon">
            历史报告
          </el-button>
          <el-button type="warning" size="small" @click="openSFTManager">
            📚 迭代数据 ({{ sftStats.total_unused }})
          </el-button>
          <el-button type="primary" size="small" @click="exportReport('json')" :icon="DocumentIcon">
            导出 JSON
          </el-button>
          <el-button type="success" size="small" @click="exportReport('csv')" :icon="DownloadIcon">
            导出 CSV
          </el-button>
          <el-tag type="info" v-if="detailedReport.experiment_info" effect="light">
            测试ID: {{ detailedReport.experiment_info.test_id }}
          </el-tag>
        </div>
      </div>

      <!-- 实验信息 -->
      <el-card v-if="detailedReport.experiment_info" class="info-card">
        <template #header>
          <span>🧪 实验配置</span>
        </template>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">实验模式:</span>
            <el-tag :type="getExperimentModeType(detailedReport.experiment_info.experiment_mode)" effect="light">
              {{ detailedReport.experiment_info.experiment_mode }}
            </el-tag>
          </div>
          <div class="info-item">
            <span class="label">RAG状态:</span>
            <el-tag :type="detailedReport.experiment_info.rag_enabled ? 'success' : 'info'" effect="light">
              {{ detailedReport.experiment_info.rag_enabled ? '启用' : '禁用' }}
            </el-tag>
          </div>
          <div class="info-item">
            <span class="label">开始时间:</span>
            <span class="value">{{ formatDateTime(detailedReport.experiment_info.start_time) }}</span>
          </div>
          <div class="info-item">
            <span class="label">耗时:</span>
            <span class="value">{{ formatDuration(detailedReport.experiment_info.duration_seconds) }}</span>
          </div>
        </div>
      </el-card>

      <!-- 总体统计卡片 -->
      <div class="stats-cards">
        <el-card class="stat-card" :body-style="{ padding: '20px' }">
          <div class="stat-value large">{{ detailedReport.summary?.total_questions || 0 }}</div>
          <div class="stat-label">总题数</div>
        </el-card>
        <el-card class="stat-card" :body-style="{ padding: '20px' }">
          <div class="stat-value large" :class="getAccuracyClass(detailedReport.summary?.accuracy_rate)">
            {{ detailedReport.summary?.accuracy_rate || 0 }}%
          </div>
          <div class="stat-label">正确率</div>
        </el-card>
        <el-card class="stat-card" :body-style="{ padding: '20px' }">
          <div class="stat-value large">{{ detailedReport.summary?.avg_score || 0 }}</div>
          <div class="stat-label">平均分</div>
        </el-card>
        <el-card class="stat-card" :body-style="{ padding: '20px' }">
          <div class="stat-value large success">{{ detailedReport.summary?.correct_count || 0 }}</div>
          <div class="stat-label">正确数</div>
        </el-card>
        <el-card class="stat-card" :body-style="{ padding: '20px' }">
          <div class="stat-value large danger">{{ detailedReport.summary?.wrong_count || 0 }}</div>
          <div class="stat-label">错误数</div>
        </el-card>
      </div>

      <!-- 图表区域 -->
      <div class="charts-section">
        <!-- 学科对比图 -->
        <el-card class="chart-card">
          <template #header>
            <span>📚 各学科正确率对比</span>
          </template>
          <div class="subject-bars">
            <div v-for="(stat, subject) in detailedReport.by_subject" :key="subject" class="subject-bar-item">
              <div class="bar-label">{{ subject }}</div>
              <div class="bar-wrapper">
                <el-progress 
                  :percentage="stat.accuracy" 
                  :color="getAccuracyColor(stat.accuracy)"
                  :stroke-width="16"
                  :show-text="true"
                />
              </div>
              <div class="bar-stats">
                <span class="correct">{{ stat.correct }}/{{ stat.total }}</span>
                <span class="avg">均分{{ stat.avg_score }}</span>
              </div>
            </div>
          </div>
        </el-card>

        <!-- 分数分布 -->
        <el-card class="chart-card">
          <template #header>
            <span>📈 分数分布</span>
          </template>
          <div class="distribution-bars">
            <div v-for="(count, range) in detailedReport.score_distribution" :key="range" class="dist-item">
              <div class="dist-label">{{ range }}分</div>
              <div class="dist-bar-wrapper">
                <div class="dist-bar" :style="{ width: getDistributionPercent(count) + '%', background: getDistributionColor(range) }"></div>
                <span class="dist-count">{{ count }}题</span>
              </div>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 所有结果表格（列头筛选排序） -->
      <el-card class="all-results-card">
        <template #header>
          <div class="card-header">
            <span>📝 详细结果列表</span>
            <div class="header-actions">
              <el-button 
                type="primary"
                size="small"
                @click="addSelectedToIteration"
                :disabled="selectedResultIds.length === 0"
                :loading="addingToIteration"
              >
                📚 加入迭代队列 ({{ selectedResultIds.length }})
              </el-button>
              <el-button 
                type="danger"
                size="small"
                plain
                @click="deleteSelectedResults"
                :disabled="selectedResultIds.length === 0"
              >
                删除 ({{ selectedResultIds.length }})
              </el-button>
            </div>
          </div>
        </template>
        <el-table 
          ref="resultsTable"
          :data="results" 
          size="small" 
          stripe
          max-height="500"
          v-loading="loading"
          @selection-change="handleResultSelectionChange"
          @filter-change="handleFilterChange"
        >
          <el-table-column type="selection" width="45" />
          <el-table-column label="序号" width="55">
            <template #default="{ $index }">
              {{ (pagination.page - 1) * pagination.page_size + $index + 1 }}
            </template>
          </el-table-column>
          <el-table-column prop="subject" label="学科" width="70">
            <template #default="{ row }">
              <el-tag size="small" :color="getSubjectColor(row.subject)" style="color: #fff; border: none;">{{ row.subject }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="year" label="年份" width="65" sortable />
          <el-table-column label="题目" min-width="180">
            <template #default="{ row }">
              <div class="text-truncate-3" v-html="renderLatex(row.question)"></div>
            </template>
          </el-table-column>
          <el-table-column label="模型回答" min-width="150">
            <template #default="{ row }">
              <pre class="text-truncate-3">{{ row.model_answer }}</pre>
            </template>
          </el-table-column>
          <el-table-column prop="correct_answer" label="正确答案" width="75" />
          <el-table-column 
            prop="is_correct" 
            label="结果"
            width="85"
            column-key="is_correct"
            :filters="[
              { text: '全部', value: 'all' },
              { text: '✓ 正确', value: true },
              { text: '✗ 错误', value: false }
            ]"
            filter-placement="bottom"
            :filtered-value="currentFilter === 'all' ? [] : [currentFilter === 'correct']"
          >
            <template #default="{ row }">
              <el-tag :type="row.is_correct ? 'success' : 'danger'" size="small" effect="light">
                {{ row.is_correct ? '✓ 正确' : '✗ 错误' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="overall_score" label="总分" width="70" sortable>
            <template #default="{ row }">
              <span :class="['score', getScoreClass(row.overall_score)]">{{ row.overall_score?.toFixed(1) || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="accuracy_score" label="准确" width="55" sortable />
          <el-table-column prop="completeness_score" label="完整" width="55" sortable />
          <el-table-column prop="educational_score" label="教育" width="55" sortable />
          <el-table-column label="操作" width="110" fixed="right">
            <template #default="{ row }">
              <div class="action-buttons">
                <el-button type="primary" size="small" @click="viewDetail(row)">详情</el-button>
                <el-button 
                  v-if="!row.is_correct || row.overall_score < 3" 
                  :type="(addedToIterationIds.has(row.id) || row.is_in_knowledge_base) ? '' : 'danger'" 
                  size="small"
                  class="learn-btn"
                  :class="{ 'learned': addedToIterationIds.has(row.id) || row.is_in_knowledge_base }"
                  :disabled="addedToIterationIds.has(row.id) || row.is_in_knowledge_base"
                  @click="addSingleToIteration(row)"
                >
                  {{ (addedToIterationIds.has(row.id) || row.is_in_knowledge_base) ? '已学习' : '学习' }}
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
        
        <div class="pagination">
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.page_size"
            :total="pagination.total"
            layout="total, prev, pager, next, sizes"
            :page-sizes="[10, 20, 50, 100]"
            @change="loadResults"
          />
        </div>
      </el-card>
    </div>

    <!-- 详情弹窗 -->
    <el-dialog
      v-model="detailVisible"
      title="题目详情"
      width="800px"
      class="detail-dialog"
    >
      <div v-if="currentDetail" class="detail-content">
        <div class="detail-header">
          <el-tag :type="getSubjectType(currentDetail.subject)" size="large" effect="light">{{ currentDetail.subject }}</el-tag>
          <span class="detail-year">{{ currentDetail.year }}年</span>
          <span class="detail-score">{{ currentDetail.score }}分</span>
        </div>
        
        <div class="detail-section">
          <h4>题目</h4>
          <div class="question-text latex-content" v-html="renderLatex(currentDetail.question)"></div>
        </div>
        
        <div class="detail-section">
          <h4>模型回答</h4>
          <pre class="answer-box model-answer-full" :class="{ wrong: !currentDetail.is_correct }">{{ currentDetail.model_answer || '无回答' }}</pre>
        </div>
        
        <div class="detail-section">
          <h4>正确答案</h4>
          <div class="answer-box correct">
            {{ currentDetail.correct_answer }}
          </div>
        </div>
        
        <div class="detail-section">
          <h4>解析</h4>
          <div class="analysis-text latex-content" v-html="renderLatex(currentDetail.analysis) || '暂无解析'"></div>
        </div>
        
        <div class="detail-section scores">
          <h4>质量评分</h4>
          <div class="score-grid">
            <div class="score-item">
              <span>准确性</span>
              <el-rate v-model="currentDetail.accuracy_score" disabled show-score />
            </div>
            <div class="score-item">
              <span>完整性</span>
              <el-rate v-model="currentDetail.completeness_score" disabled show-score />
            </div>
            <div class="score-item">
              <span>教育性</span>
              <el-rate v-model="currentDetail.educational_score" disabled show-score />
            </div>
          </div>
        </div>
        
        <div v-if="currentDetail.suggestions" class="detail-section">
          <h4>改进建议</h4>
          <p>{{ currentDetail.suggestions }}</p>
        </div>
      </div>
    </el-dialog>

    <!-- 报告管理弹窗 -->
    <el-dialog
      v-model="showReportManager"
      title="📁 历史报告管理"
      width="1000px"
      class="report-manager-dialog"
      :close-on-click-modal="false"
    >
      <div class="report-manager-content">
        <!-- 操作栏 -->
        <div class="report-actions-bar">
          <div class="action-left">
            <el-button 
              type="primary" 
              size="default"
              @click="compareSelectedReports"
              :loading="comparingReports"
              :disabled="selectedReports.length < 2"
              :icon="DocumentIcon"
            >
              对比报告
              <el-tag v-if="selectedReports.length > 0" type="warning" size="small" effect="light" class="count-tag">
                {{ selectedReports.length }}
              </el-tag>
            </el-button>
          </div>
          <div class="action-right">
            <el-button 
              type="info" 
              size="default" 
              plain
              @click="loadSavedReports" 
              :icon="Refresh"
              :loading="loadingReports"
            >
              刷新
            </el-button>
          </div>
        </div>

        <!-- 报告表格 -->
        <el-table
          :data="savedReports"
          size="small"
          stripe
          highlight-current-row
          v-loading="loadingReports"
          @selection-change="(val: string[]) => selectedReports = val.map((r: any) => r.filename)"
          class="reports-table"
        >
          <el-table-column type="selection" width="45" align="center" />
          <el-table-column prop="test_id" label="测试ID" width="150">
            <template #default="{ row }">
              <span class="test-id">{{ row.test_id }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="experiment_mode" label="模式" width="100">
            <template #default="{ row }">
              <el-tag :type="getExperimentModeType(row.experiment_mode)" size="small" effect="light">
                {{ row.experiment_mode }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="rag_enabled" label="RAG" width="60" align="center">
            <template #default="{ row }">
              <el-tag :type="row.rag_enabled ? 'success' : 'info'" size="small" effect="light">
                {{ row.rag_enabled ? '✓' : '-' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="total_questions" label="题目" width="70" align="center" />
          <el-table-column prop="accuracy_rate" label="正确率" width="85" align="center">
            <template #default="{ row }">
              <span :class="['accuracy-text', getAccuracyClass(row.accuracy_rate)]">
                {{ row.accuracy_rate }}%
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="avg_score" label="均分" width="65" align="center">
            <template #default="{ row }">
              <span class="avg-score">{{ row.avg_score }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="saved_at" label="保存时间" min-width="140">
            <template #default="{ row }">
              <span class="time-text">{{ formatDateTime(row.saved_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="110" fixed="right" align="center">
            <template #default="{ row }">
              <el-button 
                type="primary" 
                size="small" 
                text
                @click="loadReportByFilename(row.filename)"
              >
                加载
              </el-button>
              <el-button 
                type="danger" 
                size="small" 
                text
                @click="deleteSavedReport(row.filename)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 底部提示 -->
        <div class="report-tips">
          <el-alert 
            type="info" 
            :closable="false" 
            show-icon
            size="small"
          >
            <template #title>
              <span class="tip-text">选择 2 个或以上报告可生成对比分析</span>
            </template>
          </el-alert>
        </div>
      </div>
    </el-dialog>

    <!-- SFT数据管理器 -->
    <el-dialog
      v-model="showSFTManager"
      title="📚 待训练数据管理 (SFT Data)"
      width="900px"
      :close-on-click-modal="false"
    >
      <div class="sft-manager">
        <!-- 统计概览 -->
        <div class="sft-stats">
          <div class="sft-stat-card">
            <div class="sft-stat-value">{{ sftStats.total_unused }}</div>
            <div class="sft-stat-label">待训练数据</div>
          </div>
          <div class="sft-stat-card used">
            <div class="sft-stat-value">{{ sftStats.total_used }}</div>
            <div class="sft-stat-label">已训练数据</div>
          </div>
        </div>

        <!-- 按专家统计 -->
        <div v-if="sftStats.by_expert?.length > 0" class="sft-expert-list">
          <h4>按专家分布</h4>
          <div class="sft-expert-items">
            <div 
              v-for="expert in sftStats.by_expert" 
              :key="expert.expert_id"
              class="sft-expert-item"
              :class="{ active: selectedSFTExpert === expert.expert_id }"
              @click="selectedSFTExpert = selectedSFTExpert === expert.expert_id ? null : expert.expert_id; loadSFTData()"
            >
              <el-tag size="small" effect="light">{{ expert.expert_name }}</el-tag>
              <span class="sft-count">
                <el-tag type="warning" size="small" effect="light">{{ expert.unused_count }} 待入库</el-tag>
                <el-tag type="success" size="small" effect="light" v-if="expert.used_count > 0">{{ expert.used_count }} 已入库</el-tag>
              </span>
            </div>
          </div>
        </div>

        <!-- 数据列表 -->
        <el-table :data="sftDataList" size="small" stripe v-loading="loadingSFT" max-height="400">
          <el-table-column type="index" width="50" />
          <el-table-column prop="expert_name" label="专家" width="100">
            <template #default="{ row }">
              <el-tag size="small" effect="light">{{ row.expert_name }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="instruction" label="问题" show-overflow-tooltip min-width="200" />
          <el-table-column prop="quality_score" label="质量分" width="80">
            <template #default="{ row }">
              <el-tag :type="row.quality_score >= 4 ? 'success' : row.quality_score >= 3 ? 'warning' : 'danger'" size="small" effect="light">
                {{ row.quality_score }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="is_used_in_training" label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.is_used_in_training ? 'success' : 'warning'" size="small" effect="light">
                {{ row.is_used_in_training ? '已入库' : '待入库' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="140">
            <template #default="{ row }">
              {{ formatDateTime(row.created_at) }}
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-if="sftTotal > sftPageSize"
          v-model:current-page="sftPage"
          v-model:page-size="sftPageSize"
          :total="sftTotal"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          small
          @change="loadSFTData"
        />

        <div class="sft-tips">
          <el-alert type="info" :closable="false" show-icon>
            <template #title>
              提示：点击专家标签筛选数据，点击"创建训练任务"为对应专家启动微调训练
            </template>
          </el-alert>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Trophy, QuestionFilled, Document, Download, FolderOpened, Refresh, Check } from '@element-plus/icons-vue'
import { benchmarkApi, expertApi } from '../api'
import katex from 'katex'

// 导出图标
const DocumentIcon = Document
const DownloadIcon = Download
const FolderOpenedIcon = FolderOpened

// LaTeX渲染函数
const renderLatex = (text: string): string => {
  if (!text) return ''
  
  // 预处理：移除可能导致KaTeX警告的Unicode字符
  const preprocessLatex = (latex: string): string => {
    return latex
      .replace(/[（）]/g, '') // 移除中文全角括号
      .replace(/[，。、；：""''！？《》（）【】]/g, '') // 移除中文标点
  }
  
  // 匹配 $...$ 和 $$...$$ 格式的LaTeX
  return text.replace(/\$\$(.+?)\$\$/gs, (match, latex) => {
    try {
      const cleanLatex = preprocessLatex(latex)
      return katex.renderToString(cleanLatex, { 
        throwOnError: false, 
        displayMode: true,
        strict: 'ignore' // 忽略非严格模式的警告
      })
    } catch {
      return match
    }
  }).replace(/\$(.+?)\$/g, (match, latex) => {
    try {
      const cleanLatex = preprocessLatex(latex)
      return katex.renderToString(cleanLatex, { 
        throwOnError: false, 
        displayMode: false,
        strict: 'ignore' // 忽略非严格模式的警告
      })
    } catch {
      return match
    }
  })
}

// 格式化模型回答，纯文本显示
// 统计数据
const stats = ref({
  total_questions: 0,
  correct_count: 0,
  wrong_count: 0,
  accuracy_rate: 0,
  avg_score: 0,
  by_subject: {} as Record<string, number>
})

// 数据集信息
const datasetInfo = ref<any>({ exists: false })
const customDatasetPath = ref('')
const selectedImportSubject = ref('')

// 测试配置
const experts = ref<Array<{id: number; name: string; subject: string}>>([])
const selectedExpert = ref<number | 'auto'>('auto')  // 'auto' = 自动路由
const testMode = ref('all')
const testSubject = ref('')
const testYear = ref('')
const testing = ref(false)
const importing = ref(false)
const stopping = ref(false)

// 进度
const progress = ref({
  status: '',
  current: 0,
  total: 0,
  current_question: '',
  elapsed_time: 0
})
const recentResults = ref<Array<any>>([])

// 报告
const report = ref<any>({})

// 详细报告
const detailedReport = ref<any>({})
const addingToIteration = ref(false)

// 报告管理
const showReportManager = ref(false)
const savedReports = ref<Array<any>>([])
const loadingReports = ref(false)
const selectedReports = ref<string[]>([])
const comparingReports = ref(false)

// SFT数据管理
const showSFTManager = ref(false)
const sftStats = ref<any>({ total_unused: 0, total_used: 0, by_expert: [] })
const sftDataList = ref<Array<any>>([])
const loadingSFT = ref(false)
const selectedSFTExpert = ref<number | null>(null)
const sftPage = ref(1)
const sftPageSize = ref(20)
const sftTotal = ref(0)

// 结果列表
const results = ref<Array<any>>([])
const loading = ref(false)
const resultsTable = ref<any>(null)
const selectedResultIds = ref<number[]>([])
const addedToIterationIds = ref<Set<number>>(new Set())
const pagination = ref({
  page: 1,
  page_size: 20,
  total: 0
})

// 当前筛选类型
const currentFilter = ref('all')  // 'all', 'correct', 'wrong'

// 详情弹窗
const detailVisible = ref(false)
const currentDetail = ref<any>(null)

// 计算属性
const canStartTest = computed(() => {
  // 不再强制要求选择专家，支持自动路由
  return stats.value.total_questions > 0 && !testing.value
})

const progressPercentage = computed(() => {
  if (progress.value.total === 0) return 0
  return Math.round((progress.value.current / progress.value.total) * 100)
})

const progressStatus = computed(() => {
  if (progressPercentage.value === 100) return 'success'
  return ''
})

// 表格数据直接使用 results（Element Plus 表格会自己处理序号）

// 方法
const loadStats = async () => {
  try {
    const res = await benchmarkApi.getStats() as any
    stats.value = res
  } catch (error) {
    console.error('加载统计失败:', error)
  }
}

const loadDatasetInfo = async () => {
  try {
    const res = await benchmarkApi.getDatasetInfo() as any
    datasetInfo.value = res
  } catch (error) {
    console.error('加载数据集信息失败:', error)
  }
}

const loadExperts = async () => {
  try {
    const res = await expertApi.list() as any
    // API 返回 { code, message, data } 结构
    experts.value = res.data || []
  } catch (error) {
    console.error('加载专家失败:', error)
  }
}

const loadReport = async () => {
  try {
    const res = await benchmarkApi.getReport() as any
    report.value = res
    detailedReport.value = res
    console.log('详细报告:', detailedReport.value)
  } catch (error) {
    console.error('加载报告失败:', error)
  }
}

// 导出报告
const exportReport = async (format: string) => {
  try {
    const res = await benchmarkApi.exportReport(format) as any
    if (format === 'json') {
      // 下载JSON文件
      const dataStr = JSON.stringify(res, null, 2)
      const blob = new Blob([dataStr], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `benchmark_report_${detailedReport.value.experiment_info?.test_id || Date.now()}.json`
      link.click()
      URL.revokeObjectURL(url)
      ElMessage.success('JSON报告已导出')
    } else if (format === 'csv') {
      // 下载CSV文件
      const blob = new Blob([res.csv_content], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `benchmark_report_${detailedReport.value.experiment_info?.test_id || Date.now()}.csv`
      link.click()
      URL.revokeObjectURL(url)
      ElMessage.success('CSV报告已导出')
    }
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败')
  }
}

// 格式化日期时间
const formatDateTime = (isoString: string | null): string => {
  if (!isoString) return '-'
  const date = new Date(isoString)
  return date.toLocaleString('zh-CN')
}

// 格式化时长
const formatDuration = (seconds: number): string => {
  if (!seconds || seconds <= 0) return '-'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)
  if (hours > 0) {
    return `${hours}时${minutes}分${secs}秒`
  } else if (minutes > 0) {
    return `${minutes}分${secs}秒`
  } else {
    return `${secs}秒`
  }
}

// 获取实验模式标签类型
const getExperimentModeType = (mode: string): string => {
  const typeMap: Record<string, string> = {
    'baseline': 'info',
    'rag_only': 'success',
    'expert_routing': 'warning',
    'full_system': 'primary'
  }
  return typeMap[mode] || 'info'
}

// 获取准确率颜色
const getAccuracyColor = (accuracy: number): string => {
  if (accuracy >= 80) return '#67C23A'
  if (accuracy >= 60) return '#E6A23C'
  return '#F56C6C'
}

// 获取分数标签类型
// 获取分布百分比
const getDistributionPercent = (count: number | string): number => {
  const numCount = typeof count === 'string' ? parseInt(count, 10) : count
  const total = detailedReport.value.summary?.total_questions || 1
  return (numCount / total) * 100
}

// 获取分布颜色
const getDistributionColor = (range: string | number): string => {
  const rangeStr = String(range)
  const colorMap: Record<string, string> = {
    '4-5': '#67C23A',
    '3-4': '#95D475',
    '2-3': '#E6A23C',
    '1-2': '#F89898',
    '0-1': '#F56C6C'
  }
  return colorMap[rangeStr] || '#909399'
}

// 添加选中的题目到迭代（表格上方按钮使用）
const addSelectedToIteration = async () => {
  // 将 Proxy 数组转换为普通数组
  const selectedIds = JSON.parse(JSON.stringify(selectedResultIds.value))
  
  if (selectedIds.length === 0) {
    ElMessage.warning('请先选择题目')
    return
  }
  
  // 筛选出错题（正确题不需要迭代）
  const selectedItems = results.value.filter((r: any) => selectedIds.includes(r.id))
  const wrongItems = selectedItems.filter((r: any) => !r.is_correct || r.overall_score < 3)
  const correctCount = selectedItems.length - wrongItems.length
  
  if (wrongItems.length === 0) {
    ElMessage.warning('选中的题目中没有错题，只有错题可以加入迭代')
    return
  }
  
  // 确保是普通数组
  const wrongIds = wrongItems.map((r: any) => Number(r.id))
  
  try {
    addingToIteration.value = true
    const res = await benchmarkApi.addToIteration({ result_ids: wrongIds })
    
    // 显示即时反馈（现在只是加入队列，不立即生成）
    let msg = `✅ 已将 ${res.added_count || wrongIds.length} 道错题加入迭代队列`
    if (res.already_in_queue > 0) {
      msg += `（${res.already_in_queue} 道已在队列中）`
    }
    if (correctCount > 0) {
      msg += `，已跳过 ${correctCount} 道正确题`
    }
    ElMessage.success(msg)
    
    // 标记为已加入队列
    wrongIds.forEach((id: number) => addedToIterationIds.value.add(id))
    
    // 清空表格选中状态
    selectedResultIds.value = []
    if (resultsTable.value) {
      resultsTable.value.clearSelection()
    }
  } catch (error: any) {
    console.error('添加失败:', error)
    ElMessage.error(error?.response?.data?.detail || '添加失败')
  } finally {
    addingToIteration.value = false
  }
}

// 加载保存的报告列表
const loadSavedReports = async () => {
  try {
    loadingReports.value = true
    const res = await benchmarkApi.listSavedReports() as any
    savedReports.value = res.reports || []
  } catch (error) {
    console.error('加载报告列表失败:', error)
    ElMessage.error('加载报告列表失败')
  } finally {
    loadingReports.value = false
  }
}

// 加载指定报告
const loadReportByFilename = async (filename: string) => {
  try {
    const res = await benchmarkApi.loadSavedReport(filename) as any
    if (res.success) {
      detailedReport.value = res.report.results
      ElMessage.success('报告已加载')
      showReportManager.value = false
    }
  } catch (error) {
    console.error('加载报告失败:', error)
    ElMessage.error('加载报告失败')
  }
}

// 删除报告
const deleteSavedReport = async (filename: string) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除报告 ${filename} 吗？`,
      '确认删除',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    await benchmarkApi.deleteSavedReport(filename)
    ElMessage.success('报告已删除')
    await loadSavedReports()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('删除报告失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

// 对比报告
const compareSelectedReports = async () => {
  if (selectedReports.value.length < 2) {
    ElMessage.warning('请至少选择2个报告进行对比')
    return
  }
  
  try {
    comparingReports.value = true
    const res = await benchmarkApi.compareReports(selectedReports.value) as any
    ElMessage.success('对比报告已生成')
    // 下载对比报告
    const report = await benchmarkApi.loadSavedReport(res.comparison_file.split('/').pop()) as any
    const dataStr = JSON.stringify(report, null, 2)
    const blob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `comparison_${Date.now()}.json`
    link.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error('对比报告失败:', error)
    ElMessage.error('对比报告失败')
  } finally {
    comparingReports.value = false
  }
}

// 监听报告管理弹窗
watch(showReportManager, (val) => {
  if (val) {
    loadSavedReports()
  }
})

const checkLocalDataset = async () => {
  if (!customDatasetPath.value) {
    ElMessage.warning('请输入路径')
    return
  }
  await loadDatasetInfo()
}

const importLocalDataset = async () => {
  importing.value = true
  try {
    const res = await benchmarkApi.importDataset({ 
      source: 'local',
      path: datasetInfo.value.path
    }) as any
    ElMessage.success(`成功导入 ${res.imported_count} 道题目`)
    await loadStats()
    await loadDatasetInfo()
  } catch (error: any) {
    console.error('导入失败:', error)
    ElMessage.error(error?.response?.data?.detail || '导入失败')
  } finally {
    importing.value = false
  }
}

const importSubjectDataset = async () => {
  if (!selectedImportSubject.value) return
  
  importing.value = true
  try {
    const res = await benchmarkApi.importDataset({ 
      source: 'local',
      path: datasetInfo.value.path,
      subject: selectedImportSubject.value
    }) as any
    ElMessage.success(`${selectedImportSubject.value} 导入成功，共 ${res.imported_count} 道题`)
    await loadStats()
    await loadDatasetInfo()
  } catch (error: any) {
    console.error('导入失败:', error)
    ElMessage.error(error?.response?.data?.detail || '导入失败')
  } finally {
    importing.value = false
  }
}

const startBenchmark = async () => {
  // 先检查是否已有测试在运行（防止重复提交）
  try {
    const currentStatus = await benchmarkApi.getProgress() as any
    if (currentStatus.status === 'running') {
      ElMessage.warning('已有测试正在进行，已同步状态')
      testing.value = true
      progress.value = currentStatus
      startProgressPolling()
      return
    }
  } catch (e) {
    // 如果获取状态失败，继续尝试启动
    console.log('获取当前状态失败，继续启动')
  }
  
  // 设置前端状态为"启动中"
  testing.value = true
  progress.value = { status: 'running', current: 0, total: 0, current_question: '准备中...', elapsed_time: 0 }
  recentResults.value = []
  
  try {
    await benchmarkApi.startTest({
      expert_id: selectedExpert.value === 'auto' ? null : selectedExpert.value,
      mode: testMode.value,
      subject: testSubject.value,
      year: testYear.value
    })
    
    ElMessage.success('测试已启动')
    // 启动进度轮询
    startProgressPolling()
  } catch (error: any) {
    // 重置前端状态
    testing.value = false
    progress.value = { status: 'error', current: 0, total: 0, current_question: '', elapsed_time: 0 }
    
    // 判断错误类型
    let errorMsg = '启动测试失败'
    if (!error?.response) {
      errorMsg = '无法连接到后端服务 (localhost:8000)，请确保后端已启动'
    } else if (error?.response?.data?.detail) {
      errorMsg = error.response.data.detail
    }
    
    ElMessage.error(errorMsg)
    console.error('启动测试错误:', error)
    
    // 如果是"已有测试正在进行"，尝试同步状态
    if (errorMsg.includes('已有测试')) {
      syncTestStatus()
    }
  }
}

const stopBenchmark = async () => {
  try {
    stopping.value = true
    
    // 设置超时：8秒后如果还没停止，强制重置
    const timeoutId = setTimeout(async () => {
      ElMessage.warning('停止请求超时，正在强制重置...')
      try {
        const resetRes = await benchmarkApi.resetTest() as any
        if (progressTimer) {
          clearInterval(progressTimer)
          progressTimer = null
        }
        testing.value = false
        stopping.value = false
        progress.value.status = 'stopped'
        ElMessage.success(resetRes.message || '测试已强制停止')
        loadResults()
        loadStats()
        loadReport()
      } catch (e) {
        stopping.value = false
      }
    }, 8000)
    
    const res = await benchmarkApi.stopTest() as any
    clearTimeout(timeoutId)
    
    if (res.success) {
      ElMessage.info(`正在停止测试... 当前进度: ${res.stopped_at || '?'} 道题目`)
      // 状态变更会通过轮询同步
    } else {
      // 如果后端说没有测试在运行，但前端认为有，同步状态
      if (res.message?.includes('没有正在进行的测试')) {
        ElMessage.warning('后端显示没有测试在运行，同步状态')
        syncTestStatus()
      } else {
        ElMessage.warning(res.message || '停止测试失败')
      }
      stopping.value = false
    }
  } catch (error: any) {
    ElMessage.error('停止测试失败: ' + (error?.message || '未知错误'))
    stopping.value = false
  }
}

// 强制停止测试（直接调用reset，不等待后端响应）
const forceStopBenchmark = async () => {
  try {
    stopping.value = true
    ElMessage.warning('正在强制停止测试...')
    
    // 先清除定时器，防止状态混乱
    if (progressTimer) {
      clearInterval(progressTimer)
      progressTimer = null
    }
    
    // 直接调用重置API
    const res = await benchmarkApi.resetTest() as any
    
    // 立即清理前端状态
    testing.value = false
    stopping.value = false
    progress.value = { 
      status: 'stopped', 
      current: 0, 
      total: 0, 
      current_question: '', 
      elapsed_time: 0 
    }
    
    ElMessage.success(res.message || '测试已强制停止')
    
    // 刷新结果
    loadResults()
    loadStats()
    loadReport()
  } catch (error: any) {
    stopping.value = false
    ElMessage.error('强制停止失败: ' + (error?.message || '未知错误'))
    // 即使失败也重置前端状态
    testing.value = false
    if (progressTimer) {
      clearInterval(progressTimer)
      progressTimer = null
    }
  }
}

const resetBenchmark = async () => {
  try {
    const res = await benchmarkApi.resetTest() as any
    testing.value = false
    stopping.value = false
    // 清除定时器
    if (progressTimer) {
      clearInterval(progressTimer)
      progressTimer = null
    }
    ElMessage.success(res.message || '测试状态已重置')
    loadStats()
    loadReport()
  } catch (error: any) {
    ElMessage.error('重置失败: ' + (error?.message || '未知错误'))
  }
}

const loadResults = async () => {
  loading.value = true
  try {
    const res = await benchmarkApi.getResults({
      page: pagination.value.page,
      page_size: pagination.value.page_size,
      filter: currentFilter.value
    }) as any
    results.value = res.items || []
    pagination.value.total = res.total || 0
  } catch (error) {
    console.error('加载结果失败:', error)
  } finally {
    loading.value = false
  }
}

const handleResultSelectionChange = (selection: any[]) => {
  // 选中所有被选中的行
  selectedResultIds.value = selection.map(item => item.id)
}

// 处理筛选变化（当用户点击列筛选器时触发）
const handleFilterChange = (filters: any) => {
  // 处理结果列的筛选变化
  if (filters.is_correct && filters.is_correct.length > 0) {
    const value = filters.is_correct[0]
    if (value === 'all') {
      currentFilter.value = 'all'
    } else if (value === true) {
      currentFilter.value = 'correct'
    } else if (value === false) {
      currentFilter.value = 'wrong'
    }
  } else {
    currentFilter.value = 'all'
  }
  // 筛选后重置到第一页，序号会自动重新编排
  pagination.value.page = 1
  selectedResultIds.value = []
  // 从后端重新加载筛选后的数据
  loadResults()
}

const deleteSelectedResults = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedResultIds.value.length} 条测试结果吗？`,
      '确认删除',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    await benchmarkApi.deleteResults({ result_ids: selectedResultIds.value })
    ElMessage.success(`已删除 ${selectedResultIds.value.length} 条测试结果`)
    // 清空表格选中状态
    selectedResultIds.value = []
    if (resultsTable.value) {
      resultsTable.value.clearSelection()
    }
    loadResults()
    loadStats()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const addSingleToIteration = async (row: any) => {
  try {
    const res = await benchmarkApi.addToIteration({
      result_ids: [Number(row.id)]
    })
    // 标记为已加入队列
    addedToIterationIds.value.add(row.id)
    
    let msg = `✅ 已加入迭代队列`
    if (res.already_in_queue > 0) {
      msg = `已在迭代队列中`
    }
    ElMessage.success(msg)
  } catch (error: any) {
    console.error('加入迭代队列失败:', error)
    ElMessage.error(error?.response?.data?.detail || '加入迭代队列失败')
  }
}

const viewDetail = (row: any) => {
  currentDetail.value = row
  detailVisible.value = true
}

const formatTime = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const getSubjectType = (subject: string) => {
  const map: Record<string, string> = {
    '数学': 'success',
    '语文': 'primary',
    '英语': 'warning',
    '物理': 'info',
    '化学': 'danger',
    '生物': 'success',
    '政治': 'danger',
    '历史': 'info',
    '地理': 'warning'
  }
  return map[subject] || 'info'
}

// 使用更深、更明显的颜色
const getSubjectColor = (subject: string): string => {
  const map: Record<string, string> = {
    '数学': '#2E7D32',    // 深绿色
    '语文': '#1565C0',    // 深蓝色
    '英语': '#E65100',    // 深橙色
    '物理': '#00695C',    // 深青色
    '化学': '#C62828',    // 深红色
    '生物': '#558B2F',    // 橄榄绿
    '政治': '#AD1457',    // 深粉色
    '历史': '#4527A0',    // 深紫色
    '地理': '#EF6C00'     // 深橙色
  }
  return map[subject] || '#5C63A9'
}

const getSubjectTagType = (subject: string) => {
  const map: Record<string, any> = {
    '数学': 'success',
    '语文': 'primary',
    '英语': 'warning',
    '物理': 'info',
    '化学': 'danger',
    '生物': 'success',
    '政治': 'danger',
    '历史': 'info',
    '地理': 'warning'
  }
  return map[subject] || 'info'
}

const getScoreClass = (score: number) => {
  if (score >= 4) return 'high'
  if (score >= 3) return 'medium'
  return 'low'
}

const getAccuracyClass = (rate: number) => {
  if (rate >= 70) return 'high'
  if (rate >= 50) return 'medium'
  return 'low'
}

// ============ SFT数据管理函数 ============
const openSFTManager = async () => {
  showSFTManager.value = true
  await loadSFTStats()
  await loadSFTData()
}

const loadSFTStats = async () => {
  try {
    const res = await benchmarkApi.getSFTStats() as any
    sftStats.value = res
  } catch (error) {
    console.error('加载SFT统计失败:', error)
  }
}

const loadSFTData = async () => {
  loadingSFT.value = true
  try {
    const params: any = {
      page: sftPage.value,
      page_size: sftPageSize.value
    }
    if (selectedSFTExpert.value !== null) {
      params.expert_id = selectedSFTExpert.value
    }
    const res = await benchmarkApi.getSFTData(params) as any
    sftDataList.value = res.items || []
    sftTotal.value = res.total || 0
  } catch (error) {
    console.error('加载SFT数据失败:', error)
  } finally {
    loadingSFT.value = false
  }
}

onMounted(() => {
  loadStats()
  loadDatasetInfo()
  loadExperts()
  loadResults()
  loadReport()
  // 检查是否有正在运行的测试，同步状态
  syncTestStatus()
})

// 同步后端测试状态（解决页面刷新后状态丢失问题）
let progressTimer: number | null = null
let syncInProgress = false

const syncTestStatus = async () => {
  if (syncInProgress) return
  syncInProgress = true
  
  try {
    const status = await benchmarkApi.getProgress() as any
    
    // 根据后端状态同步前端
    if (status.status === 'running') {
      // 后端正在运行，同步到前端
      if (!testing.value) {
        ElMessage.info('检测到正在进行的测试，已同步状态')
      }
      testing.value = true
      progress.value = status
      // 启动轮询（如果还没启动）
      if (!progressTimer) {
        startProgressPolling()
      }
    } else if (status.status === 'completed') {
      // 测试已完成
      testing.value = false
      progress.value = status
      if (progressTimer) {
        clearInterval(progressTimer)
        progressTimer = null
      }
      loadResults()
      loadStats()
      loadReport()
    } else if (status.status === 'stopped') {
      // 测试被停止
      testing.value = false
      progress.value = status
      if (progressTimer) {
        clearInterval(progressTimer)
        progressTimer = null
      }
      loadResults()
      loadStats()
      loadReport()
    } else if (status.status === 'error') {
      // 测试出错
      testing.value = false
      progress.value = status
      if (progressTimer) {
        clearInterval(progressTimer)
        progressTimer = null
      }
      ElMessage.error('测试过程出错: ' + (status.error || '未知错误'))
    }
    // status === 'idle' 或其他：前端保持当前状态
  } catch (error) {
    console.error('同步测试状态失败:', error)
    // 连接失败，不修改前端状态，让用户知道可能断连了
  } finally {
    syncInProgress = false
  }
}

// 启动进度轮询（抽取为独立函数）
const startProgressPolling = () => {
  // 清除已有定时器
  if (progressTimer) {
    clearInterval(progressTimer)
    progressTimer = null
  }
  
  // 立即获取一次状态
  syncTestStatus()
  
  progressTimer = window.setInterval(async () => {
    try {
      const status = await benchmarkApi.getProgress() as any
      
      // 更新进度信息
      progress.value = status
      
      // 只在进度变化时更新最近完成的题目
      if (status.recent_results && status.recent_results.length > 0) {
        const newIds = new Set(recentResults.value.map(r => r.id))
        const newItems = status.recent_results.filter((r: any) => !newIds.has(r.id))
        if (newItems.length > 0) {
          recentResults.value = [...newItems, ...recentResults.value].slice(0, 20) // 最多保留20条
        }
      }
      
      // 检查测试是否结束
      if (status.status === 'completed' || (status.total > 0 && status.current >= status.total)) {
        if (progressTimer) {
          clearInterval(progressTimer)
          progressTimer = null
        }
        testing.value = false
        stopping.value = false
        ElMessage.success(`测试完成！共完成 ${status.current} 道题目`)
        loadResults()
        loadStats()
        loadReport()
      } else if (status.status === 'stopped') {
        if (progressTimer) {
          clearInterval(progressTimer)
          progressTimer = null
        }
        testing.value = false
        stopping.value = false
        ElMessage.info(`测试已停止，已完成 ${status.current} 道题目`)
        loadResults()
        loadStats()
        loadReport()
      } else if (status.status === 'error' || status.status === 'failed') {
        if (progressTimer) clearInterval(progressTimer)
        testing.value = false
        stopping.value = false
        ElMessage.error('测试出错')
      }
    } catch (error) {
      if (progressTimer) clearInterval(progressTimer)
      testing.value = false
      stopping.value = false
    }
  }, 1500)  // 1.5秒轮询一次，更快响应停止操作
}
</script>

<style scoped lang="scss">
.benchmark-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
  overflow-y: auto;
}

.page-header {
  background: linear-gradient(135deg, #5C63A9 0%, #4CC9BB 100%);
  border: 3px solid #111;
  box-shadow: 6px 6px 0 0 #111;
  padding: 24px;
  color: white;

  .header-title {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;

    h1 {
      font-family: 'Space Grotesk', sans-serif;
      font-size: 28px;
      font-weight: 700;
      margin: 0;
    }
  }

  .header-desc {
    margin: 0;
    opacity: 0.9;
    font-size: 14px;
  }
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  padding: 4px;

  .stat-card {
    background: white;
    border: 3px solid #111;
    box-shadow: 4px 4px 0 0 #111;
    padding: 16px;
    display: flex;
    align-items: center;
    gap: 12px;
    transition: all 0.2s;

    &:hover {
      transform: translate(-2px, -2px);
      box-shadow: 6px 6px 0 0 #111;
    }

    &.blue { background: #3F51B5; color: white; }      // 靛蓝
    &.green { background: #2E7D32; color: white; }     // 深绿
    &.red { background: #C62828; color: white; }       // 深红
    &.yellow { background: #F57F17; color: white; }    // 深橙黄
    &.purple { background: #6A1B9A; color: white; }    // 深紫

    .stat-icon {
      font-size: 32px;
    }

    .stat-value {
      font-family: 'Space Grotesk', sans-serif;
      font-size: 28px;
      font-weight: 700;
    }

    .stat-label {
      font-size: 12px;
      opacity: 0.8;
      font-weight: 600;
    }
  }
}

.action-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;

  .action-card {
    background: white;
    border: 3px solid #111;
    box-shadow: 4px 4px 0 0 #111;
    padding: 20px;

    h3 {
      font-family: 'Space Grotesk', sans-serif;
      margin: 0 0 16px 0;
      font-size: 16px;
    }

    .dataset-status {
      .dataset-detail {
        margin-top: 8px;
        p {
          margin: 4px 0;
          font-size: 13px;
        }
      }

      .subject-tags {
        margin-top: 12px;
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        align-items: center;
        font-size: 13px;

        .subject-tag {
          cursor: default;
        }
      }

      .import-actions {
        margin-top: 16px;
        display: flex;
        gap: 12px;
        align-items: center;

        .subject-select {
          width: 180px;
        }
      }
    }

    .dataset-missing {
      .import-form {
        margin-top: 16px;
        display: flex;
        gap: 12px;

        .path-input {
          flex: 1;
        }
      }
    }

    .debug-info {
      margin-top: 12px;

      .debug-items {
        display: flex;
        flex-direction: column;
        gap: 4px;
        font-size: 12px;
        margin-top: 4px;

        span {
          color: #f56c6c;

          &.ok {
            color: #67c23a;
          }
        }
      }
    }

    .test-config {
      .config-row {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 12px;

        label {
          font-weight: 600;
          width: 80px;
          font-size: 13px;
        }

        .config-select {
          flex: 1;
        }

        .help-icon {
          color: #999;
          cursor: help;
          font-size: 16px;

          &:hover {
            color: #5C63A9;
          }
        }
      }
    }
  }
}

.progress-section {
  .progress-card {
    background: white;
    border: 3px solid #111;
    box-shadow: 4px 4px 0 0 #111;
    padding: 20px;
    transition: all 0.3s ease;
    
    // 不同状态的样式
    &.idle {
      background: #f8f9fa;
      border-color: #adb5bd;
      box-shadow: 4px 4px 0 0 #adb5bd;
      
      .status-title {
        color: #6c757d;
      }
      
      .status-icon.idle {
        color: #adb5bd;
      }
      
      :deep(.el-progress-bar__outer) {
        background-color: #e9ecef;
      }
    }
    
    &.running {
      background: white;
      border-color: #111;
      box-shadow: 4px 4px 0 0 #111;
      animation: pulse-border 2s infinite;
      
      .status-title {
        color: #5C63A9;
      }
      
      .status-icon.running {
        color: #5C63A9;
        animation: spin 1s linear infinite;
      }
    }
    
    &.completed {
      background: #f0f9f0;
      border-color: #28a745;
      box-shadow: 4px 4px 0 0 #28a745;
      
      .status-title {
        color: #28a745;
      }
      
      .status-icon.completed {
        color: #28a745;
      }
    }

    .progress-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      font-weight: 600;
      
      .status-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-family: 'Space Grotesk', sans-serif;
        font-size: 16px;
        
        .status-icon {
          font-size: 20px;
        }
      }

      .progress-actions {
        display: flex;
        align-items: center;
        gap: 12px;
        
        .progress-count {
          font-family: 'DM Mono', monospace;
          font-size: 14px;
          color: #666;
          background: #f0f0f0;
          padding: 2px 10px;
          border-radius: 12px;
          border: 2px solid #111;
        }
      }

      .stop-btn {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 4px;
      }
    }

    .progress-detail {
      display: flex;
      justify-content: space-between;
      margin-top: 12px;
      font-size: 13px;
      color: #666;

      .progress-time {
        font-family: 'DM Mono', monospace;
        background: #f8f9fa;
        padding: 2px 8px;
        border-radius: 4px;
        border: 1px solid #dee2e6;
      }
      
      .status-desc {
        font-style: italic;
        color: #6c757d;
      }

      .latex-content {
        :deep(.katex) {
          font-size: 0.85em;
        }
      }
    }
  }

  .recent-results {
    margin-top: 16px;
    background: white;
    border: 2px solid #111;
    box-shadow: 3px 3px 0 0 #111;
    padding: 12px 16px;
    height: auto;
    max-height: 200px;
    display: flex;
    flex-direction: column;
    
    &.empty {
      max-height: 120px;
      padding: 8px 16px;
      
      :deep(.el-empty) {
        padding: 0;
        
        .el-empty__description {
          margin-top: 4px;
        }
      }
      
      .empty-text {
        font-size: 12px;
        color: #adb5bd;
      }
    }

    h4 {
      font-family: 'Space Grotesk', sans-serif;
      margin: 0 0 8px 0;
      font-size: 13px;
      color: #666;
      flex-shrink: 0;
    }

    .recent-table {
      flex: 1;
      
      :deep(.el-table__body-wrapper) {
        overflow: hidden;
      }
      
      :deep(.el-table__row) {
        height: 28px;
        
        td {
          padding: 2px 0;
        }
      }
      
      .recent-index {
        font-size: 12px;
        color: #999;
        font-family: 'DM Mono', monospace;
      }
      
      .result-tag {
        padding: 0 4px;
        height: 18px;
        font-size: 11px;
      }
      
      .recent-question {
        font-size: 12px;
        color: #333;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      
      .recent-score {
        font-size: 12px;
        font-weight: 600;
        font-family: 'DM Mono', monospace;
      }
      
      .latex-content {
        :deep(.katex) {
          font-size: 0.9em;
        }
      }
    }
  }
}

.report-section {
  .report-card {
    background: white;
    border: 3px solid #111;
    box-shadow: 4px 4px 0 0 #111;
    padding: 20px;

    h3 {
      font-family: 'Space Grotesk', sans-serif;
      margin: 0 0 16px 0;
    }

    .report-summary {
      display: flex;
      gap: 32px;
      margin-bottom: 20px;
      padding: 16px;
      background: #f5f5f5;
      border: 2px solid #111;

      .report-item {
        .label {
          font-size: 12px;
          color: #666;
          margin-right: 8px;
        }
        .value {
          font-family: 'Space Grotesk', sans-serif;
          font-size: 24px;
          font-weight: 700;

          &.high { color: #4CC9BB; }
          &.medium { color: #F28E70; }
          &.low { color: #FF78A5; }
        }
      }
    }

    .subject-report {
      h4 {
        font-family: 'Space Grotesk', sans-serif;
        margin: 0 0 12px 0;
        font-size: 14px;
      }
    }
  }
}

.results-section {
  flex: 1;
  background: white;
  border: 3px solid #111;
  box-shadow: 4px 4px 0 0 #111;
  display: flex;
  flex-direction: column;
  min-height: 400px;

  .results-header {
    padding: 16px 20px;
    border-bottom: 3px solid #111;
    display: flex;
    justify-content: space-between;
    align-items: center;

    h3 {
      font-family: 'Space Grotesk', sans-serif;
      margin: 0;
    }

    .results-filters {
      display: flex;
      gap: 12px;
      align-items: center;
    }
  }

  .results-table {
    flex: 1;

    :deep(.el-table__header) {
      background: #f5f5f5;
    }

    .score {
      font-weight: 700;
      font-family: 'DM Mono', monospace;

      &.high { color: #2E7D32; }      // 深绿色
      &.medium { color: #E65100; }    // 深橙色
      &.low { color: #C62828; }       // 深红色
    }

    .latex-content {
      :deep(.katex) {
        font-size: 1em;
      }
    }
  }

  .pagination {
    padding: 16px;
    border-top: 2px solid #eee;
    display: flex;
    justify-content: flex-end;
  }
}

.detail-content {
  .detail-header {
    display: flex;
    gap: 12px;
    align-items: center;
    margin-bottom: 20px;
    padding-bottom: 12px;
    border-bottom: 2px solid #eee;

    .detail-year, .detail-score {
      font-family: 'DM Mono', monospace;
      font-size: 14px;
      color: #666;
    }
  }

  .detail-section {
    margin-bottom: 20px;

    h4 {
      font-family: 'Space Grotesk', sans-serif;
      margin: 0 0 8px 0;
      font-size: 14px;
    }

    .question-text, .analysis-text {
      margin: 0;
      padding: 12px;
      background: #f5f5f5;
      border: 2px solid #111;
      line-height: 1.6;
      white-space: pre-wrap;
      font-family: inherit;
    }

    .answer-box {
      padding: 12px;
      border: 2px solid #111;
      background: #f5f5f5;

      &.correct {
        background: #e8f5e9;
        border-color: #2E7D32;
      }

      &.wrong {
        background: #ffebee;
        border-color: #C62828;
      }

      &.model-answer-full {
        font-family: 'DM Mono', monospace;
        font-size: 13px;
        white-space: pre-wrap;
        word-wrap: break-word;
        max-height: 400px;
        overflow-y: auto;
        line-height: 1.6;
        background: #fafafa;
      }
    }

    .latex-content {
      :deep(.katex) {
        font-size: 1.1em;
      }
      :deep(.katex-display) {
        margin: 0.5em 0;
      }
    }

    &.scores {
      .score-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
      }

      .score-item {
        display: flex;
        flex-direction: column;
        gap: 8px;

        span {
          font-weight: 600;
          font-size: 13px;
        }
      }
    }
  }
}

// 详细报告样式
.detailed-report-section {
  display: flex;
  flex-direction: column;
  gap: 20px;

  .report-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: white;
    border: 3px solid #111;
    box-shadow: 4px 4px 0 0 #111;
    padding: 16px 20px;

    h3 {
      font-family: 'Space Grotesk', sans-serif;
      margin: 0;
      font-size: 20px;
    }

    .report-actions {
      display: flex;
      gap: 12px;
      align-items: center;
    }
  }

  .info-card {
    border: 3px solid #111;
    box-shadow: 4px 4px 0 0 #111;

    .info-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;

      .info-item {
        display: flex;
        flex-direction: column;
        gap: 4px;

        .label {
          font-size: 12px;
          color: #666;
          font-weight: 600;
        }

        .value {
          font-family: 'DM Mono', monospace;
          font-size: 14px;
        }
      }
    }
  }

  .stats-cards {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 16px;

    .stat-card {
      border: 3px solid #111;
      box-shadow: 4px 4px 0 0 #111;
      text-align: center;

      .stat-value {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 32px;
        font-weight: 700;
        margin-bottom: 8px;

        &.large {
          font-size: 36px;
        }

        &.success { color: #67C23A; }
        &.danger { color: #F56C6C; }
        &.high { color: #67C23A; }
        &.medium { color: #E6A23C; }
        &.low { color: #F56C6C; }
      }

      .stat-label {
        font-size: 12px;
        color: #666;
        font-weight: 600;
      }
    }
  }

  .charts-section {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 20px;

    .chart-card {
      border: 3px solid #111;
      box-shadow: 4px 4px 0 0 #111;

      :deep(.el-card__header) {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        border-bottom: 2px solid #111;
      }
    }
  }

  .subject-bars {
    display: flex;
    flex-direction: column;
    gap: 16px;

    .subject-bar-item {
      display: grid;
      grid-template-columns: 80px 1fr 120px;
      gap: 12px;
      align-items: center;

      .bar-label {
        font-weight: 600;
        font-size: 14px;
      }

      .bar-wrapper {
        :deep(.el-progress__text) {
          font-family: 'DM Mono', monospace;
          font-weight: 700;
        }
      }

      .bar-stats {
        display: flex;
        flex-direction: column;
        font-size: 11px;
        color: #666;

        .correct {
          font-weight: 600;
          color: #333;
        }
      }
    }
  }

  .distribution-bars {
    display: flex;
    flex-direction: column;
    gap: 12px;

    .dist-item {
      display: flex;
      align-items: center;
      gap: 12px;

      .dist-label {
        width: 50px;
        font-size: 12px;
        font-weight: 600;
      }

      .dist-bar-wrapper {
        flex: 1;
        display: flex;
        align-items: center;
        gap: 8px;

        .dist-bar {
          height: 20px;
          border-radius: 4px;
          transition: width 0.3s;
        }

        .dist-count {
          font-size: 12px;
          color: #666;
          font-family: 'DM Mono', monospace;
        }
      }
    }
  }

  .report-manager-dialog {
    :deep(.el-dialog__header) {
      background: linear-gradient(135deg, #5C63A9 0%, #4CC9BB 100%);
      color: white;
      padding: 16px 20px;
      margin-right: 0;
      
      .el-dialog__title {
        color: white;
        font-weight: 600;
      }
      
      .el-dialog__headerbtn .el-dialog__close {
        color: white;
      }
    }

    :deep(.el-dialog__body) {
      padding: 0;
    }

    :deep(.el-dialog) {
      border: 2px solid #dcdfe6;
      border-radius: 12px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
    }

    .report-manager-content {
      padding: 16px 20px;

      .report-actions-bar {
        margin-bottom: 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: nowrap;
        gap: 12px;
        padding-bottom: 16px;
        border-bottom: 1px solid #ebeef5;

        .action-left, .action-right {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .count-tag {
          margin-left: 4px;
          font-size: 11px;
          padding: 0 6px;
          height: 18px;
          line-height: 16px;
        }
      }

      .reports-table {
        border: 1px solid #dcdfe6;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);

        :deep(.el-table__header) {
          background: #f5f7fa;
          
          th {
            background: #f5f7fa;
            font-weight: 600;
            color: #606266;
            padding: 12px 0;
            font-size: 13px;
          }
        }

        :deep(.el-table__row) {
          cursor: pointer;
          
          &:hover {
            background: #f5f7fa;
          }

          &.current-row {
            background: #ecf5ff;
          }

          td {
            padding: 10px 0;
          }
        }

        .test-id {
          font-family: 'DM Mono', monospace;
          font-size: 12px;
          color: #606266;
        }

        .accuracy-text {
          font-weight: 600;
          
          &.high { color: #67C23A; }
          &.medium { color: #E6A23C; }
          &.low { color: #F56C6C; }
        }

        .avg-score {
          font-weight: 600;
          color: #409EFF;
        }

        .time-text {
          font-size: 12px;
          color: #909399;
        }
      }

      .report-tips {
        margin-top: 16px;
        
        .tip-text {
          font-size: 13px;
          color: #606266;
        }
      }
    }
  }

  .wrong-questions-card,
  .all-results-card {
    border: 3px solid #111;
    box-shadow: 4px 4px 0 0 #111;

    :deep(.el-card__header) {
      border-bottom: 2px solid #111;
    }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-family: 'Space Grotesk', sans-serif;
      font-weight: 700;
    }

    // 操作按钮样式
    .action-buttons {
      display: flex;
      flex-direction: column;
      gap: 6px;
      align-items: flex-start;

      .el-button {
        padding: 0 6px;
        height: 22px;
        line-height: 22px;
        font-size: 12px;
        border: 2px solid #111;
        box-shadow: 2px 2px 0 0 #111;
        transition: all 0.1s;
        font-weight: 600;
        
        &:hover:not(:disabled) {
          transform: translate(-1px, -1px);
          box-shadow: 3px 3px 0 0 #111;
        }
        
        &:active:not(:disabled) {
          transform: translate(2px, 2px);
          box-shadow: 0 0 0 0 #111;
        }
      }

      // 详情按钮 - 蓝色
      .el-button--primary {
        background: #1565C0;
        color: white;
        border-color: #111;
        
        &:hover:not(:disabled) {
          background: #0D47A1;
        }
      }

      // 学习按钮
      .learn-btn {
        // 未学习状态 - 红色背景
        &.el-button--danger {
          background: #C62828;
          color: white;
          border-color: #111;
          margin-left: 0;
          
          &:hover:not(:disabled) {
            background: #B71C1C;
          }
        }

        // 已学习状态 - 深灰色背景
        &.learned {
          background: #424242;
          color: #E0E0E0;
          border-color: #212121;
          box-shadow: none;
          margin-left: -4px;
          padding: 0 4px;
          
          &:hover {
            background: #424242;
            color: #E0E0E0;
          }
        }
      }
    }
  }
}


@media (max-width: 1200px) {
  .stats-cards {
    grid-template-columns: repeat(3, 1fr);
  }

  .action-section {
    grid-template-columns: 1fr;
  }

  .detailed-report-section {
    .charts-section {
      grid-template-columns: 1fr;
    }

    .info-card .info-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }
}

@media (max-width: 768px) {
  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
  }

  .detailed-report-section {
    .stats-cards {
      grid-template-columns: repeat(2, 1fr);
    }

    .info-card .info-grid {
      grid-template-columns: 1fr;
    }
  }
}

// SFT数据管理器样式
.sft-manager {
  .sft-stats {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
    margin-bottom: 20px;

    .sft-stat-card {
      background: white;
      border: 3px solid #111;
      box-shadow: 4px 4px 0 0 #111;
      padding: 16px;
      text-align: center;

      &.used {
        background: #E8F5E9;
      }

      .sft-stat-value {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 32px;
        font-weight: 700;
        color: #111;
      }

      .sft-stat-label {
        font-size: 13px;
        color: #666;
        font-weight: 600;
        margin-top: 4px;
      }
    }
  }

  .sft-expert-list {
    margin-bottom: 20px;
    padding: 16px;
    background: #f9f9f9;
    border: 2px solid #111;

    h4 {
      font-family: 'Space Grotesk', sans-serif;
      margin: 0 0 12px 0;
    }

    .sft-expert-items {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;

      .sft-expert-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 16px;
        background: white;
        border: 2px solid #111;
        box-shadow: 3px 3px 0 0 #111;
        cursor: pointer;
        transition: all 0.2s;

        &:hover, &.active {
          transform: translate(-2px, -2px);
          box-shadow: 5px 5px 0 0 #111;
          border-color: #5C63A9;
        }

        &.active {
          background: #FFF8E1;
        }

        .sft-count {
          display: flex;
          gap: 8px;
        }
      }
    }
  }

  .sft-tips {
    margin-top: 16px;
  }
}

// 全局文本截断样式（必须放在 scoped style 之外）
.text-truncate-3 {
  display: -webkit-box !important;
  -webkit-line-clamp: 3 !important;
  -webkit-box-orient: vertical !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  line-height: 1.5 !important;
  max-height: 4.5em !important;
  white-space: pre-wrap !important;
  word-wrap: break-word !important;
}

.text-truncate-3 pre {
  display: -webkit-box !important;
  -webkit-line-clamp: 3 !important;
  -webkit-box-orient: vertical !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  line-height: 1.5 !important;
  max-height: 4.5em !important;
  white-space: pre-wrap !important;
  word-wrap: break-word !important;
  margin: 0 !important;
  padding: 0 !important;
  font-family: inherit !important;
}

// 动画定义
@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@keyframes pulse-border {
  0% {
    box-shadow: 4px 4px 0 0 #111;
  }
  50% {
    box-shadow: 4px 4px 0 0 #5C63A9, 0 0 15px rgba(92, 99, 169, 0.3);
  }
  100% {
    box-shadow: 4px 4px 0 0 #111;
  }
}
</style>
