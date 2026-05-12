<template>
  <div class="report-view">
    <!-- 决策概览卡片 -->
    <div class="decision-overview">
      <div class="fund-info">
        <h2 class="fund-title">
          <span class="fund-code">{{ report?.fundCode }}</span>
          <span class="fund-name">{{ report?.fundName }}</span>
        </h2>
        <span class="update-time">更新时间：{{ formatTime(report?.updatedAt || '') }}</span>
      </div>
      <div class="decision-cards">
        <div class="decision-card short-term">
          <div class="decision-label">短线建议（7-30天）</div>
          <div class="decision-direction" :class="shortTermDirection">
            {{ shortTermDirectionText }}
          </div>
          <div class="decision-detail">
            <span class="holding-period">建议持有期：{{ formatHoldingPeriod(report?.decision.shortTerm.holdingPeriod) }}</span>
            <span class="confidence">置信度：{{ (report?.decision.shortTerm.confidence || 0) * 100 }}%</span>
          </div>
        </div>
        <div class="decision-card long-term">
          <div class="decision-label">长线建议（6个月以上）</div>
          <div class="decision-direction" :class="longTermDirection">
            {{ longTermDirectionText }}
          </div>
          <div class="decision-detail">
            <span class="dip-suggestion">{{ report?.decision.longTerm.dipSuggestion || '长期持有' }}</span>
            <span class="confidence">置信度：{{ (report?.decision.longTerm.confidence || 0) * 100 }}%</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 走势图展示区 -->
    <div class="trend-chart-section">
      <div class="section-header">
        <h3>净值走势与预测</h3>
        <div class="chart-legend" v-if="report?.trendData?.historical?.length">
          <span class="legend-item historical">
            <span class="legend-color"></span>
            历史走势
          </span>
          <span class="legend-item prediction">
            <span class="legend-color"></span>
            预测走势
          </span>
        </div>
      </div>
      <div class="chart-container" v-if="report?.trendData?.historical?.length">
        <div ref="trendChartRef" class="echarts-container"></div>
      </div>
      <div class="chart-no-data" v-else>
        <p>暂无走势数据</p>
      </div>
      <div class="chart-note" v-if="report?.trendData?.historical?.length">
        注：预测走势仅供参考，不构成投资建议。实际走势可能与预测存在较大差异。
      </div>
    </div>

    <!-- 智能体评分雷达图 -->
    <div class="radar-chart-section">
      <h3>智能体评分总览</h3>
      <div class="radar-chart-wrapper" v-if="report?.scores">
        <div ref="radarChartRef" class="echarts-container radar-chart"></div>
      </div>
      <div class="chart-no-data" v-else>
        <p>暂无评分数据</p>
      </div>
    </div>

    <!-- 成本矩阵表格 -->
    <div class="cost-matrix-section">
      <h3>成本矩阵</h3>
      <table class="cost-table">
        <thead>
          <tr>
            <th>建议持有期</th>
            <th>申购费率</th>
            <th>赎回费率</th>
            <th>总费率</th>
            <th>盈亏平衡点</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in report?.costMatrix"
            :key="row.holdingPeriod"
            :class="{ recommended: row.recommended }"
          >
            <td>
              {{ row.holdingPeriod }}
              <span v-if="row.recommended"> [推荐]</span>
            </td>
            <td>{{ row.purchaseFee }}</td>
            <td>{{ row.redemptionFee }}</td>
            <td>{{ row.totalFee }}</td>
            <td>{{ row.breakEvenPoint }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 短线/长线详细建议区 -->
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
              <li v-for="(reason, index) in report?.shortTermDetail.reasons" :key="index">
                {{ reason }}
              </li>
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
              <li v-for="(reason, index) in report?.longTermDetail.reasons" :key="index">
                {{ reason }}
              </li>
            </ul>
          </div>
          <div class="suggestion-item" v-if="report?.longTermDetail.dipSuggestion">
            <span class="item-label">定投建议：</span>
            <span class="item-value">{{ report?.longTermDetail.dipSuggestion }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 综合风险提示区 -->
    <div class="risk-alert-section">
      <h3>风险提示</h3>
      <div class="risk-list" v-if="report?.riskAlerts?.length">
        <div
          v-for="(alert, index) in report?.riskAlerts"
          :key="index"
          class="risk-item"
        >
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
</template>

<script setup lang="ts">
/* 工作台报告视图组件 */

import { formatTime, formatHoldingPeriod } from '~/utils/format'
import { useWorkspaceCharts } from '~/composables/useWorkspaceCharts'
import type { AnalysisReport } from '~/services/analysis.service'

const props = defineProps<{
  /* 分析报告数据 */
  report: AnalysisReport | null
}>()

/* 图表管理 */
const {
  trendChartRef,
  radarChartRef,
  updateChartsDelayed,
  handleResize,
  disposeCharts,
} = useWorkspaceCharts()

/* 暴露图表方法给父组件 */
defineExpose({
  updateChartsDelayed: () => updateChartsDelayed(props.report),
  handleResize,
  disposeCharts,
})

/* 短线决策方向 */
const shortTermDirection = computed(() => props.report?.decision.shortTerm.direction || 'hold')

/* 短线决策文本 */
const shortTermDirectionText = computed(() => {
  const direction = shortTermDirection.value
  const map: Record<string, string> = { buy: '买入', sell: '卖出', hold: '持有' }
  return map[direction] || '持有'
})

/* 长线决策方向 */
const longTermDirection = computed(() => props.report?.decision.longTerm.direction || 'hold')

/* 长线决策文本 */
const longTermDirectionText = computed(() => {
  const direction = longTermDirection.value
  const map: Record<string, string> = { buy: '买入', sell: '卖出', hold: '持有' }
  return map[direction] || '持有'
})

/* 监听报告变化更新图表 */
watch(() => props.report, (newReport) => {
  if (newReport) {
    updateChartsDelayed(newReport)
  }
})

/* 组件挂载时初始化图表 */
onMounted(() => {
  if (props.report) {
    updateChartsDelayed(props.report)
  }
  window.addEventListener('resize', handleResize)
})

/* 组件卸载时清理 */
onUnmounted(() => {
  disposeCharts()
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.echarts-container {
  width: 100%;
  height: 300px;
}

.echarts-container.radar-chart {
  height: 250px;
}

.chart-no-data {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #909399;
  font-size: 14px;
  background: #f5f7fa;
  border-radius: 8px;
  margin: 10px 0;
}
</style>
