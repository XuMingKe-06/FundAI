<template>
  <div class="landing-page">
    <!-- 导航栏 -->
    <nav class="navbar">
      <div class="nav-container">
        <div class="nav-logo">
          <svg class="logo-icon" width="32" height="32" viewBox="0 0 32 32" fill="none">
            <rect x="2" y="20" width="6" height="10" rx="1" fill="#3B82F6"/>
            <rect x="10" y="14" width="6" height="16" rx="1" fill="#60A5FA"/>
            <rect x="18" y="8" width="6" height="22" rx="1" fill="#3B82F6"/>
            <rect x="26" y="2" width="4" height="28" rx="1" fill="#60A5FA"/>
            <path d="M4 18 L12 12 L20 16 L28 6" stroke="#3B82F6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          </svg>
          <span class="logo-text">FundAI</span>
        </div>
        <div class="nav-right">
          <!-- 工作台按钮 -->
          <button class="btn-workspace" @click="navigateToWorkspacePage">工作台</button>
          <!-- 设置按钮，跳转到设置页面 -->
          <NuxtLink to="/settings" class="btn-settings">
            设置
          </NuxtLink>
        </div>
      </div>
    </nav>

    <!-- Hero区域 -->
    <section class="hero-section scroll-section" data-section="hero">
      <div class="hero-container">
        <h1 class="hero-title">多智能体<span class="highlight-text">场外基金</span>分析决策系统</h1>
        <p class="hero-subtitle">基于AI多智能体协作，为您提供经过成本校验的短线与长线投资建议</p>

        <!-- 搜索区域 -->
        <div class="search-area">
          <div class="search-bar">
            <div class="search-bar-prefix">
              <RiskSelect v-model="riskPreference" />
            </div>
            <input
              v-model="fundInput"
              type="text"
              class="search-input"
              placeholder="输入基金代码或名称，如：000001 或 华夏成长"
              autocomplete="off"
              @input="onFundInput"
              @focus="onFundInput"
            >
            <button class="search-btn" @click="startAnalysis">分析决策</button>
            <div
              class="search-suggestions"
              :class="{ active: showSuggestions }"
              :style="suggestionsStyle"
            >
              <!-- 加载状态 -->
              <div v-if="fundService.isSearching.value" class="suggestion-loading">
                搜索中...
              </div>
              <!-- 搜索结果 -->
              <div
                v-else
                v-for="item in suggestionItems"
                :key="item.fundCode"
                class="suggestion-item"
                @click="selectFund(item.fundCode, item.fundName)"
              >
                {{ item.fundCode }} - {{ item.fundName }}
              </div>
              <!-- 无结果提示 -->
              <div
                v-if="!fundService.isSearching.value && suggestionItems.length === 0 && fundInput.trim()"
                class="suggestion-empty"
              >
                未找到匹配的基金
              </div>
              <!-- 错误提示 -->
              <div
                v-if="fundService.searchError.value"
                class="suggestion-error"
              >
                {{ fundService.searchError.value }}
              </div>
            </div>
          </div>
          <div class="search-tips">
            <span class="tip-item">支持基金代码查询</span>
            <span class="tip-divider">·</span>
            <span class="tip-item">支持基金名称搜索</span>
            <span class="tip-divider">·</span>
            <span class="tip-item">实时数据分析</span>
          </div>
        </div>
      </div>
    </section>

    <!-- 三步流程 -->
    <section class="process-section scroll-section" data-section="process">
      <div class="section-container">
        <h2 class="section-title">三步完成基金分析决策</h2>
        <p class="section-subtitle">无需复杂操作，快速获取专业投资建议</p>
        <div class="process-grid">
          <div class="process-card">
            <div class="process-number">01</div>
            <h3>输入基金信息</h3>
            <p>输入基金代码或名称，选择您的风险偏好类型</p>
          </div>
          <div class="process-card">
            <div class="process-number">02</div>
            <h3>智能体协作分析</h3>
            <p>六个专业智能体并行分析，从多维度全面评估基金</p>
          </div>
          <div class="process-card">
            <div class="process-number">03</div>
            <h3>获取决策建议</h3>
            <p>获得短线与长线两套独立决策建议，包含详细依据</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 功能特点区 -->
    <section class="features-section scroll-section" data-section="features" id="features">
      <div class="section-container">
        <h2 class="section-title">核心功能特点</h2>
        <p class="section-subtitle">专业、透明、可信赖的基金分析服务</p>
        <div class="features-grid">
          <div class="feature-card">
            <div class="feature-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <circle cx="12" cy="12" r="4"></circle>
                <line x1="12" y1="2" x2="12" y2="4"></line>
                <line x1="12" y1="20" x2="12" y2="22"></line>
                <line x1="2" y1="12" x2="4" y2="12"></line>
                <line x1="20" y1="12" x2="22" y2="12"></line>
              </svg>
            </div>
            <h3>多智能体协作</h3>
            <p>六个专业智能体并行分析，从基本面、技术面、风险、成本、情绪等多维度全面评估</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="20" x2="18" y2="10"></line>
                <line x1="12" y1="20" x2="12" y2="4"></line>
                <line x1="6" y1="20" x2="6" y2="14"></line>
              </svg>
            </div>
            <h3>双轨决策</h3>
            <p>同时输出短线（7-30天）与长线（6个月以上）两套独立决策建议</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect>
                <line x1="1" y1="10" x2="23" y2="10"></line>
              </svg>
            </div>
            <h3>成本透明</h3>
            <p>精确计算不同持有期下的申赎成本，杜绝推荐预期净收益为负的操作</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
              </svg>
            </div>
            <h3>风险提示</h3>
            <p>针对场外基金特点提供明确的风险提示与约束说明</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
              </svg>
            </div>
            <h3>可解释性</h3>
            <p>展示每个智能体的分析依据和评分，增强决策信任</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
              </svg>
            </div>
            <h3>会话记忆</h3>
            <p>支持多轮对话交互，记录历史偏好与关注点</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 智能体展示区 -->
    <section class="agents-section scroll-section" data-section="agents" id="agents">
      <div class="section-container">
        <h2 class="section-title">专业智能体团队</h2>
        <p class="section-subtitle">每个智能体专注于特定领域，提供专业分析</p>
        <div class="agents-grid">
          <div class="agent-card">
            <div class="agent-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
                <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
                <line x1="12" y1="22.08" x2="12" y2="12"></line>
              </svg>
            </div>
            <h3>基本面分析师</h3>
            <p>评估基金底层资产质量、基金经理能力及长期竞争力</p>
          </div>
          <div class="agent-card">
            <div class="agent-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
              </svg>
            </div>
            <h3>技术分析师</h3>
            <p>基于净值历史数据判断趋势阶段、估值水平及走势预测</p>
          </div>
          <div class="agent-card">
            <div class="agent-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
              </svg>
            </div>
            <h3>风险分析师</h3>
            <p>量化评估波动风险、下行风险、流动性风险等风险暴露</p>
          </div>
          <div class="agent-card">
            <div class="agent-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="12" y1="1" x2="12" y2="23"></line>
                <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
              </svg>
            </div>
            <h3>成本分析师</h3>
            <p>精确计算不同持有期下的申赎成本，为决策提供量化约束</p>
          </div>
          <div class="agent-card">
            <div class="agent-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                <circle cx="12" cy="12" r="3"></circle>
              </svg>
            </div>
            <h3>情绪分析师</h3>
            <p>通过舆情、资金流等数据捕捉市场情绪热度</p>
          </div>
          <div class="agent-card">
            <div class="agent-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
              </svg>
            </div>
            <h3>决策智能体</h3>
            <p>汇总各分析结果，基于成本约束生成双轨决策建议</p>
          </div>
        </div>
      </div>
    </section>

    <!-- FAQ区域 -->
    <section class="faq-section scroll-section" data-section="faq">
      <div class="section-container">
        <h2 class="section-title">常见问题</h2>
        <p class="section-subtitle">关于基金分析决策的常见问题解答</p>
        <div class="faq-grid">
          <div class="faq-item">
            <h3>什么是双轨决策？</h3>
            <p>双轨决策是指系统同时提供短线（7-30天）和长线（6个月以上）两套独立的投资建议，帮助您根据不同的投资周期做出决策。</p>
          </div>
          <div class="faq-item">
            <h3>分析结果的可信度如何？</h3>
            <p>系统采用多智能体协作分析，每个智能体专注于特定领域，并提供详细的分析依据和评分，增强决策的透明度和可信度。</p>
          </div>
          <div class="faq-item">
            <h3>如何理解成本分析？</h3>
            <p>系统会精确计算不同持有期下的申购费、赎回费等成本，确保推荐的操作在扣除成本后仍具有正向收益预期。</p>
          </div>
          <div class="faq-item">
            <h3>数据更新频率如何？</h3>
            <p>基金净值数据每日更新，持仓数据按季度更新（可能存在15-45天滞后），舆情数据实时更新。</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 页脚 -->
    <footer class="footer">
      <div class="footer-container">
        <div class="footer-main">
          <div class="footer-brand">
            <span class="footer-logo">FundAI</span>
            <p class="footer-desc">多智能体场外基金分析决策系统</p>
          </div>
          <div class="footer-links">
            <div class="footer-column">
              <h4>关于我们</h4>
              <a href="#">公司介绍</a>
              <a href="#">团队成员</a>
              <a href="#">联系我们</a>
            </div>
            <div class="footer-column">
              <h4>产品服务</h4>
              <a href="#">功能介绍</a>
              <a href="#">使用指南</a>
              <a href="#">API文档</a>
            </div>
            <div class="footer-column">
              <h4>法律条款</h4>
              <a href="#">使用条款</a>
              <a href="#">隐私政策</a>
              <a href="#">免责声明</a>
            </div>
          </div>
        </div>
        <div class="footer-disclaimer">
          <p>免责声明：本系统提供的分析结论仅供用户参考，不作为投资决策的唯一依据。基金投资有风险，入市需谨慎。</p>
          <p>Copyright 2026 FundAI. All rights reserved.</p>
        </div>
      </div>
    </footer>

    <!-- 区域指示器 -->
    <div class="section-indicator">
      <div
        v-for="(section, index) in sections"
        :key="section.key"
        class="indicator-dot"
        :class="{ active: currentSectionIndex === index }"
        @click="scrollToSection(index)"
      >
        <span class="indicator-tooltip">{{ section.name }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/* 导入基金搜索服务 */
import { useFundService, type FundSearchItem } from '~/composables/useFundService'
import { ElMessage } from 'element-plus'

const router = useRouter()

/* 基金搜索服务实例 */
const fundService = useFundService()

/* 搜索相关状态 */
const fundInput = ref('')
const riskPreference = ref('neutral')
const showSuggestions = ref(false)
const suggestionsStyle = ref<Record<string, string>>({})

/* 搜索结果列表 - 从 API 获取 */
const suggestionItems = ref<FundSearchItem[]>([])

/* 区域配置 - 用于滚动吸附导航 */
const sections = [
  { key: 'hero', name: '首页' },
  { key: 'process', name: '三步完成基金分析决策' },
  { key: 'features', name: '核心功能特点' },
  { key: 'agents', name: '专业智能体团队' },
  { key: 'faq', name: '常见问题' }
]

/* 使用滚动吸附功能 */
const {
  currentSectionIndex,
  scrollToSection,
  initScrollSnap,
  destroyScrollSnap
} = useScrollSnap(sections)

/* 搜索输入处理 - 调用 API 搜索基金 */
function onFundInput() {
  const keyword = fundInput.value.trim()
  if (keyword.length > 0) {
    showSuggestions.value = true
    updateSuggestionsPosition()
    /* 使用防抖搜索 */
    fundService.debouncedSearchFunds(keyword, (results) => {
      suggestionItems.value = results
    })
  } else {
    showSuggestions.value = false
    suggestionItems.value = []
  }
}

/* 更新搜索建议下拉框位置，使其与输入框对齐 */
function updateSuggestionsPosition() {
  nextTick(() => {
    const searchBar = document.querySelector('.search-bar') as HTMLElement
    const prefix = document.querySelector('.search-bar-prefix') as HTMLElement
    const btn = document.querySelector('.search-btn') as HTMLElement
    if (searchBar && prefix && btn) {
      const prefixWidth = prefix.offsetWidth
      const btnWidth = btn.offsetWidth
      suggestionsStyle.value = {
        left: prefixWidth + 'px',
        width: (searchBar.offsetWidth - prefixWidth - btnWidth) + 'px',
        minWidth: '400px'
      }
    }
  })
}

/* 选择基金 - 填入输入框后直接跳转到工作台 */
function selectFund(code: string, name: string) {
  fundInput.value = code + ' - ' + name
  showSuggestions.value = false
  navigateToWorkspace(code)
}

/* 跳转到工作台并发起分析 */
function navigateToWorkspace(fundCode: string) {
  router.push({
    path: '/workspace',
    query: {
      fund: fundCode,
      preference: riskPreference.value
    }
  })
}

/* 跳转到工作台页面（不带基金参数） */
function navigateToWorkspacePage() {
  router.push('/workspace')
}

/* 开始分析 - 验证输入后跳转到工作台 */
function startAnalysis() {
  const inputValue = fundInput.value.trim()
  if (!inputValue) {
    ElMessage.warning('请输入基金代码或名称')
    return
  }

  /* 提取基金代码（格式可能是 "000001" 或 "000001 - 华夏成长混合"） */
  const fundCode = inputValue.split(' - ')[0].trim()

  /* 验证基金代码格式 */
  if (!/^\d{6}$/.test(fundCode)) {
    ElMessage.warning('请输入有效的6位基金代码')
    return
  }

  navigateToWorkspace(fundCode)
}

/* 点击搜索建议外部关闭下拉框 */
function handleClickOutside(event: MouseEvent) {
  const input = document.querySelector('.search-input')
  const suggestions = document.querySelector('.search-suggestions')
  if (input && suggestions && !input.contains(event.target as Node) && !suggestions.contains(event.target as Node)) {
    showSuggestions.value = false
  }
}

onMounted(() => {
  /* 注册全局点击事件监听 */
  document.addEventListener('click', handleClickOutside)
  /* 初始化滚动吸附功能 */
  initScrollSnap()
})

onUnmounted(() => {
  /* 移除全局点击事件监听 */
  document.removeEventListener('click', handleClickOutside)
  /* 销毁滚动吸附功能 */
  destroyScrollSnap()
  /* 清理基金搜索服务的定时器 */
  fundService.cleanup()
})
</script>
