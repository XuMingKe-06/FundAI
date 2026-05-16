<template>
  <div class="report-view">
    <!-- 执行摘要区 -->
    <WorkspaceExecutiveSummary
      :fund-code="report?.fundCode || ''"
      :fund-name="report?.fundName || ''"
      :short-term-direction="shortTermDirection"
      :long-term-direction="longTermDirection"
      :short-term-confidence="report?.decision.shortTerm.confidence || 0"
      :long-term-confidence="report?.decision.longTerm.confidence || 0"
      :scores="report?.scores || defaultScores"
      :risk-alerts="report?.riskAlerts || []"
    />

    <!-- 渐进式信息披露：详细分析区（可折叠） -->
    <div class="report-sections">
      <!-- 综合评分仪表盘 -->
      <div class="report-section">
        <div class="section-header" @click="toggleSection('gauge')">
          <h3>综合评分</h3>
          <span class="collapse-icon" :class="{ expanded: expandedSections.gauge }">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
          </span>
        </div>
        <div v-show="expandedSections.gauge" class="section-body">
          <div class="gauge-row">
            <div class="gauge-chart-wrapper">
              <div ref="gaugeChartRef" class="echarts-container gauge-chart"></div>
            </div>
            <div class="score-details">
              <div class="score-item" v-for="item in scoreItems" :key="item.name">
                <span class="score-name">{{ item.name }}</span>
                <div class="score-bar-wrapper">
                  <div class="score-bar" :style="{ width: `${(item.value / 5) * 100}%`, background: item.color }"></div>
                </div>
                <span class="score-value">{{ item.value.toFixed(1) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 走势图展示区 -->
      <div class="report-section">
        <div class="section-header" @click="toggleSection('trend')">
          <h3>净值走势与预测</h3>
          <span class="collapse-icon" :class="{ expanded: expandedSections.trend }">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
          </span>
        </div>
        <div v-show="expandedSections.trend" class="section-body">
          <div class="chart-legend" v-if="report?.trendData?.historical?.length">
            <span class="legend-item historical"><span class="legend-color"></span>历史走势</span>
            <span class="legend-item prediction"><span class="legend-color"></span>预测走势</span>
          </div>
          <div class="chart-container" v-if="report?.trendData?.historical?.length">
            <div ref="trendChartRef" class="echarts-container"></div>
          </div>
          <div class="chart-no-data" v-else><p>暂无走势数据</p></div>
          <div class="chart-note" v-if="report?.trendData?.historical?.length">
            注：预测走势仅供参考，不构成投资建议。实际走势可能与预测存在较大差异。
          </div>
        </div>
      </div>

      <!-- 成本矩阵表格 -->
      <div class="report-section">
        <div class="section-header" @click="toggleSection('cost')">
          <h3>成本矩阵</h3>
          <span class="collapse-icon" :class="{ expanded: expandedSections.cost }">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
          </span>
        </div>
        <div v-show="expandedSections.cost" class="section-body">
          <CommonDataTable
            :columns="costColumns"
            :data="costTableData"
            :stripe="true"
          />
        </div>
      </div>

      <!-- 短线/长线详细建议区 -->
      <div class="report-section">
        <div class="section-header" @click="toggleSection('suggestions')">
          <h3>详细建议</h3>
          <span class="collapse-icon" :class="{ expanded: expandedSections.suggestions }">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
          </span>
        </div>
        <div v-show="expandedSections.suggestions" class="section-body">
          <div class="detailed-suggestions">
            <div class="suggestion-card short-term">
              <h3>短线详细建议</h3>
              <div class="suggestion-content">
                <div class="suggestion-item">
                  <span class="item-label">操作方向：</span>
                  <span class="item-value" :class="shortTermDirection">{{ shortTermDirectionText }}</span>
                </div>
                <div class="suggestion-item">
                  <span class="item-label">建议持有期：</span>
                  <span class="item-value">{{ formatHoldingPeriod(report?.shortTermDetail.holdingPeriod) }}</span>
                </div>
                <div class="suggestion-item">
                  <span class="item-label">核心依据：</span>
                  <ul class="reason-list">
                    <li v-for="(reason, index) in report?.shortTermDetail.reasons" :key="index">{{ reason }}</li>
                  </ul>
                </div>
                <div class="suggestion-item">
                  <span class="item-label">止盈参考：</span>
                  <span class="item-value">{{ report?.shortTermDetail.stopProfit }}</span>
                </div>
                <div class="suggestion-item">
                  <span class="item-label">止损参考：</span>
                  <span class="item-value">{{ report?.shortTermDetail.stopLoss }}</span>
                </div>
              </div>
            </div>
            <div class="suggestion-card long-term">
              <h3>长线详细建议</h3>
              <div class="suggestion-content">
                <div class="suggestion-item">
                  <span class="item-label">操作方向：</span>
                  <span class="item-value" :class="longTermDirection">{{ longTermDirectionText }}</span>
                </div>
                <div class="suggestion-item">
                  <span class="item-label">核心依据：</span>
                  <ul class="reason-list">
                    <li v-for="(reason, index) in report?.longTermDetail.reasons" :key="index">{{ reason }}</li>
                  </ul>
                </div>
                <div class="suggestion-item" v-if="report?.longTermDetail.dipSuggestion">
                  <span class="item-label">定投建议：</span>
                  <span class="item-value">{{ report?.longTermDetail.dipSuggestion }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 风险提示 -->
      <div class="risk-alert-section">
        <h3>风险提示</h3>
        <div class="risk-list" v-if="report?.riskAlerts?.length">
          <div v-for="(alert, index) in report?.riskAlerts" :key="index" class="risk-item">
            <span class="risk-icon">[!]</span>
            <span class="risk-text">{{ alert }}</span>
          </div>
        </div>
        <div class="risk-list" v-else>
          <div class="risk-item">
            <span class="risk-icon">[!]</span>
            <span class="risk-text">投资有风险，入市需谨慎。本报告仅供参考，不构成投资建议。</span>
          </div>
        </div>
      </div>

      <!-- 免责声明 -->
      <div class="disclaimer">
        <p>免责声明：本报告由AI智能体自动生成，基于公开数据及算法分析，不构成任何投资建议。市场有风险，投资需谨慎。</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { formatTime, formatHoldingPeriod } from '~/utils/format'
import { useWorkspaceCharts } from '~/composables/useWorkspaceCharts'
import { useGaugeChart } from '~/composables/useGaugeChart'
import type { AnalysisReport } from '~/services/analysis.service'

const props = defineProps<{
  report: AnalysisReport | null
}>()

const defaultScores = { fundamental: 3.0, technical: 3.0, risk: 3.0, cost: 3.0, sentiment: 0.0, overall: 3.0 }

const {
  trendChartRef,
  radarChartRef,
  updateChartsDelayed,
  handleResize,
  disposeCharts,
} = useWorkspaceCharts()

const gaugeChartRef = ref<HTMLElement | null>(null)
const { buildGaugeOption } = useGaugeChart()

const expandedSections = reactive({
  gauge: true,
  trend: true,
  cost: true,
  suggestions: false,
})

function toggleSection(key: keyof typeof expandedSections) {
  expandedSections[key] = !expandedSections[key]
}

const shortTermDirection = computed(() => props.report?.decision.shortTerm.direction || 'hold')
const shortTermDirectionText = computed(() => {
  const map: Record<string, string> = { buy: '买入', sell: '卖出', hold: '持有' }
  return map[shortTermDirection.value] || '持有'
})
const longTermDirection = computed(() => props.report?.decision.longTerm.direction || 'hold')
const longTermDirectionText = computed(() => {
  const map: Record<string, string> = { buy: '买入', sell: '卖出', hold: '持有' }
  return map[longTermDirection.value] || '持有'
})

const scoreItems = computed(() => {
  const s = props.report?.scores || defaultScores
  return [
    { name: '基本面', value: s.fundamental, color: '#3B82F6' },
    { name: '技术面', value: s.technical, color: '#8B5CF6' },
    { name: '风险', value: s.risk, color: '#10B981' },
    { name: '成本', value: s.cost, color: '#F59E0B' },
    { name: '情绪', value: s.sentiment, color: '#94A3B8' },
  ]
})

const costColumns = [
  { key: 'holdingPeriod', label: '建议持有期' },
  { key: 'purchaseFee', label: '申购费率' },
  { key: 'redemptionFee', label: '赎回费率' },
  { key: 'totalFee', label: '总费率' },
  { key: 'breakEvenPoint', label: '盈亏平衡点' },
]

const costTableData = computed(() => {
  return (props.report?.costMatrix || []).map(row => ({
    ...row,
    _highlight: row.recommended,
  }))
})

async function initGaugeChart() {
  if (!gaugeChartRef.value) return
  const echarts = await import('echarts/core').then(m => m)
  const chart = echarts.init(gaugeChartRef.value)
  const overall = props.report?.scores?.overall ?? 3.0
  chart.setOption(buildGaugeOption({ value: overall, label: '综合评分' }))
}

defineExpose({
  updateChartsDelayed: () => updateChartsDelayed(props.report),
  handleResize,
  disposeCharts,
})

watch(() => props.report, (newReport) => {
  if (newReport) {
    updateChartsDelayed(newReport)
    nextTick(() => initGaugeChart())
  }
})

onMounted(() => {
  if (props.report) {
    updateChartsDelayed(props.report)
    nextTick(() => initGaugeChart())
  }
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  disposeCharts()
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.report-sections {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.report-section {
  background: var(--bg-elevated);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: background-color var(--transition-base);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3) var(--space-4);
  cursor: pointer;
  user-select: none;
  transition: background var(--transition-fast);
}

.section-header:hover {
  background: var(--bg-hover);
}

.section-header h3 {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.collapse-icon {
  display: flex;
  align-items: center;
  color: var(--text-muted);
  transition: transform var(--transition-fast);
}

.collapse-icon.expanded {
  transform: rotate(180deg);
}

.section-body {
  padding: 0 var(--space-4) var(--space-4);
}

.gauge-row {
  display: flex;
  gap: var(--space-6);
  align-items: center;
}

.gauge-chart-wrapper {
  flex: 0 0 240px;
  height: 200px;
}

.gauge-chart {
  width: 100%;
  height: 200px;
}

.score-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.score-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.score-name {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  width: 48px;
  flex-shrink: 0;
}

.score-bar-wrapper {
  flex: 1;
  height: 8px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.score-bar {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width var(--transition-slow);
}

.score-value {
  font-size: var(--text-sm);
  font-family: var(--font-data);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  width: 32px;
  text-align: right;
  flex-shrink: 0;
}

.echarts-container {
  width: 100%;
  height: 300px;
}

.chart-no-data {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: var(--text-muted);
  font-size: var(--text-base);
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  margin: var(--space-2) 0;
}

.chart-legend {
  display: flex;
  gap: var(--space-5);
  margin-bottom: var(--space-2);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.legend-color {
  width: 24px;
  height: 3px;
  border-radius: 2px;
}

.legend-item.historical .legend-color {
  background: var(--color-long-term);
}

.legend-item.prediction .legend-color {
  background: var(--color-short-term);
}

.chart-note {
  margin-top: var(--space-3);
  font-size: var(--text-xs);
  color: var(--text-muted);
  font-style: italic;
}

.detailed-suggestions {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-2);
}

.suggestion-card {
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  transition: background-color var(--transition-base);
}

.suggestion-card.short-term {
  border-top: 3px solid var(--color-short-term);
}

.suggestion-card.long-term {
  border-top: 3px solid var(--color-long-term);
}

.suggestion-card h3 {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  margin-bottom: var(--space-3);
}

.suggestion-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.suggestion-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.item-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.item-value {
  font-size: var(--text-base);
  color: var(--text-primary);
}

.item-value.buy {
  color: var(--color-buy);
  font-weight: var(--font-semibold);
}

.item-value.sell {
  color: var(--color-sell);
  font-weight: var(--font-semibold);
}

.item-value.hold {
  color: var(--color-hold);
  font-weight: var(--font-semibold);
}

.reason-list {
  list-style: none;
  padding-left: 0;
}

.reason-list li {
  position: relative;
  padding-left: var(--space-4);
  margin-bottom: var(--space-1);
  font-size: var(--text-base);
}

.reason-list li::before {
  content: ">";
  position: absolute;
  left: 0;
  color: var(--color-primary-500);
}

.risk-alert-section {
  background: var(--color-danger-50);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  margin-bottom: var(--space-2);
  border: 1px solid var(--color-danger-100);
  box-shadow: var(--shadow-base);
  transition: background-color var(--transition-base), border-color var(--transition-base);
}

.risk-alert-section h3 {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-danger-500);
  margin-bottom: var(--space-3);
}

.risk-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.risk-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
}

.risk-icon {
  color: var(--color-danger-500);
  font-weight: bold;
}

.risk-text {
  font-size: var(--text-base);
  color: var(--color-danger-700);
}

.disclaimer {
  text-align: center;
  padding: var(--space-4);
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  color: var(--text-muted);
  box-shadow: var(--shadow-base);
  transition: background-color var(--transition-base);
}

@media (max-width: 768px) {
  .detailed-suggestions {
    grid-template-columns: 1fr;
  }
  .gauge-row {
    flex-direction: column;
  }
  .gauge-chart-wrapper {
    flex: none;
    width: 100%;
  }
}
</style>
