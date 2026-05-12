/**
 * 工作台图表管理组合式函数
 *
 * 封装走势图和雷达图的初始化、更新、调整大小和销毁逻辑
 */

import { useTrendChart, useRadarChart, useChartManager } from '~/composables/useEcharts'
import type { AnalysisReport } from '~/services/analysis.service'

export function useWorkspaceCharts() {
  const trendChartRef = ref<HTMLElement | null>(null)
  const radarChartRef = ref<HTMLElement | null>(null)
  const trendChartManager = useChartManager()
  const radarChartManager = useChartManager()

  /* 更新图表 */
  async function updateCharts(report: AnalysisReport | null) {
    if (!report) return

    /* 更新走势图 */
    if (report.trendData?.historical?.length && trendChartRef.value) {
      const trendOption = useTrendChart(
        report.trendData.historical,
        report.trendData.prediction
      )
      if (trendChartManager.chartId.value) {
        trendChartManager.update(trendOption)
      } else {
        await trendChartManager.init(trendChartRef.value, trendOption)
      }
    }

    /* 更新雷达图 */
    if (report.scores && radarChartRef.value) {
      const radarOption = useRadarChart([
        {
          name: '综合评分',
          value: [
            report.scores.fundamental,
            report.scores.technical,
            report.scores.risk,
            report.scores.cost,
            report.scores.sentiment
          ]
        }
      ])
      if (radarChartManager.chartId.value) {
        radarChartManager.update(radarOption)
      } else {
        await radarChartManager.init(radarChartRef.value, radarOption)
      }
    }
  }

  /* 延迟更新图表（确保DOM渲染完成） */
  async function updateChartsDelayed(report: AnalysisReport | null) {
    await nextTick()
    if (import.meta.client) {
      await new Promise<void>(resolve => requestAnimationFrame(() => resolve()))
    }
    await updateCharts(report)
  }

  /* 窗口大小变化时调整图表 */
  function handleResize() {
    trendChartManager.resize()
    radarChartManager.resize()
  }

  /* 销毁所有图表 */
  function disposeCharts() {
    trendChartManager.dispose()
    radarChartManager.dispose()
  }

  return {
    trendChartRef,
    radarChartRef,
    trendChartManager,
    radarChartManager,
    updateCharts,
    updateChartsDelayed,
    handleResize,
    disposeCharts,
  }
}
