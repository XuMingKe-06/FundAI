/**
 * ECharts 图表 composable
 *
 * ECharts 核心库使用动态 import 懒加载，避免工作台页面首次加载时
 * 同步解析 ~1MB 的 JS 阻塞主线程。
 */

/* ==== 类型导入（编译时擦除，不产生运行时开销） ==== */
import type { ComposeOption } from 'echarts/core'
import type { BarSeriesOption, LineSeriesOption, PieSeriesOption, RadarSeriesOption } from 'echarts/charts'
import type {
  TitleComponentOption,
  TooltipComponentOption,
  GridComponentOption,
  LegendComponentOption,
  GridSimpleComponentOption,
} from 'echarts/components'
import { ref, onUnmounted } from 'vue'

/* ==== ECharts 懒加载 ==== */

/* 缓存的 echarts 核心模块引用 */
let _echartsModule: any = null
/* 并发保护：多个 initChart 调用只触发一次加载 */
let _echartsLoading: Promise<any> | null = null

/** 按需加载并注册 ECharts 组件（首次调用时异步加载 ~1MB 库） */
async function ensureEcharts(): Promise<any> {
  if (_echartsModule) return _echartsModule
  if (_echartsLoading) return _echartsLoading

  _echartsLoading = (async () => {
    const [core, charts, components, renderers, features] = await Promise.all([
      import('echarts/core'),
      import('echarts/charts'),
      import('echarts/components'),
      import('echarts/renderers'),
      import('echarts/features'),
    ])

    core.use([
      charts.BarChart, charts.LineChart, charts.PieChart, charts.RadarChart,
      components.TitleComponent, components.TooltipComponent, components.GridComponent,
      components.GridSimpleComponent, components.LegendComponent,
      components.DataZoomComponent, components.ToolboxComponent,
      components.VisualMapComponent,
      renderers.CanvasRenderer,
      features.LegacyGridContainLabel,
    ])

    _echartsModule = core
    return core
  })()

  return _echartsLoading
}

/* ==== 类型导出 ==== */

export type ECOption = ComposeOption<
  | BarSeriesOption
  | PieSeriesOption
  | LineSeriesOption
  | RadarSeriesOption
  | TitleComponentOption
  | TooltipComponentOption
  | GridComponentOption
  | GridSimpleComponentOption
  | LegendComponentOption
>

export interface TrendDataItem {
  date: string
  value: number
}

export interface PredictDataItem {
  date: string
  value: number
  lower?: number
  upper?: number
}

export interface RadarScoreData {
  name: string
  value: number[]
}

export interface RadarIndicator {
  name: string
  max: number
}

/* ==== 颜色与默认配置 ==== */

export const chartColors = {
  primary: '#409EFF',
  success: '#67C23A',
  warning: '#E6A23C',
  danger: '#F56C6C',
  info: '#909399',
  historical: '#409EFF',
  predicted: '#E6A23C',
  confidence: 'rgba(230, 162, 60, 0.2)',
  radar: ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#909399'],
}

export const defaultChartOptions: ECOption = {
  title: {
    left: 'center',
    textStyle: { fontSize: 16, fontWeight: 'bold' },
  },
  tooltip: {
    trigger: 'axis',
    confine: true,
  },
  legend: {
    bottom: 10,
    left: 'center',
  },
  grid: {
    left: '5%',
    right: '5%',
    bottom: '15%',
    top: '15%',
    containLabel: true,
  },
}

/* ==== 图表实例存储 ==== */

const chartInstances = new Map<string, any>()

const generateId = (): string => {
  return `chart_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

/* ==== 图表操作（init 异步，其余同步） ==== */

/** 初始化图表（异步：首次调用时加载 ECharts 核心） */
export const initChart = async (
  container: HTMLElement,
  options?: ECOption,
  chartId?: string
): Promise<{ id: string; chart: any }> => {
  const echarts = await ensureEcharts()
  const id = chartId || generateId()

  let chart = chartInstances.get(id)
  if (chart) {
    chart.dispose()
  }

  chart = echarts.init(container)
  chartInstances.set(id, chart)

  if (options) {
    chart.setOption(options)
  }

  return { id, chart }
}

/** 更新图表（同步，使用已有实例） */
export const updateChart = (chartId: string, options: ECOption): void => {
  const chart = chartInstances.get(chartId)
  if (chart) {
    chart.setOption(options, true)
  }
}

/** 调整图表大小（同步） */
export const resizeChart = (chartId: string): void => {
  const chart = chartInstances.get(chartId)
  if (chart) {
    chart.resize()
  }
}

/** 销毁图表（同步） */
export const disposeChart = (chartId: string): void => {
  const chart = chartInstances.get(chartId)
  if (chart) {
    chart.dispose()
    chartInstances.delete(chartId)
  }
}

/* ==== Y轴范围计算 ==== */

interface YAxisRange {
  min: number
  max: number
}

const roundToPrecision = (value: number, dataRange: number): number => {
  let precision = 2
  if (dataRange < 0.01) precision = 5
  else if (dataRange < 0.1) precision = 4
  else if (dataRange < 1) precision = 3

  const factor = Math.pow(10, precision)
  return Math.round(value * factor) / factor
}

const calculateYAxisRange = (
  historicalValues: number[],
  predictValues: (number | null)[],
  lowerValues: (number | null)[],
  upperValues: (number | null)[]
): YAxisRange | null => {
  const allValues = [
    ...historicalValues,
    ...predictValues.filter((v): v is number => v !== null && v !== undefined),
    ...lowerValues.filter((v): v is number => v !== null && v !== undefined),
    ...upperValues.filter((v): v is number => v !== null && v !== undefined),
  ]

  if (allValues.length === 0) return null

  const dataMin = Math.min(...allValues)
  const dataMax = Math.max(...allValues)
  const range = dataMax - dataMin

  if (range === 0) {
    const baseValue = dataMin
    const fixedPadding = Math.abs(baseValue) * 0.08 || 0.05
    return {
      min: roundToPrecision(baseValue - fixedPadding, fixedPadding),
      max: roundToPrecision(baseValue + fixedPadding, fixedPadding),
    }
  }

  const paddingRatio = 0.1
  const padding = range * paddingRatio

  return {
    min: roundToPrecision(dataMin - padding, range),
    max: roundToPrecision(dataMax + padding, range),
  }
}

/* ==== 走势图选项构建 ==== */

export const useTrendChart = (
  historicalData: TrendDataItem[],
  predictData?: PredictDataItem[]
) => {
  const dates = historicalData.map(item => item.date)
  const historicalValues = historicalData.map(item => item.value)

  const predictDates = predictData?.map(item => item.date) || []
  const allDates = [...dates, ...predictDates]

  const predictValues: (number | null)[] = new Array(dates.length).fill(null)
  predictData?.forEach((item) => {
    predictValues.push(item.value)
  })

  const lowerValues: (number | null)[] = new Array(dates.length).fill(null)
  predictData?.forEach((item) => {
    lowerValues.push(item.lower ?? null)
  })

  const upperValues: (number | null)[] = new Array(dates.length).fill(null)
  predictData?.forEach((item) => {
    upperValues.push(item.upper ?? null)
  })

  const yRange = calculateYAxisRange(historicalValues, predictValues, lowerValues, upperValues)

  const option: ECOption = {
    ...defaultChartOptions,
    title: { text: '净值走势图', left: 'center' },
    tooltip: {
      trigger: 'axis',
      confine: true,
      formatter: (params: any) => {
        let result = `<div style="font-weight: bold;">${params[0].axisValue}</div>`
        params.forEach((item: any) => {
          if (item.value !== null && item.value !== undefined) {
            result += `<div>${item.marker} ${item.seriesName}: ${item.value.toFixed(4)}</div>`
          }
        })
        return result
      },
    },
    legend: {
      data: ['历史走势', '预测走势', '置信区间'],
      bottom: 10,
    },
    xAxis: {
      type: 'category',
      data: allDates,
      boundaryGap: false,
      axisLabel: {
        rotate: 45,
        interval: Math.floor(allDates.length / 10),
      },
    },
    yAxis: {
      type: 'value',
      name: '净值',
      ...(yRange ? { min: yRange.min, max: yRange.max } : { scale: true }),
      splitLine: { lineStyle: { type: 'dashed' } },
      axisLabel: {
        formatter: (value: number) => {
          const range = yRange ? (yRange.max - yRange.min) : 1
          let precision = 2
          if (range < 0.01) precision = 5
          else if (range < 0.1) precision = 4
          else if (range < 1) precision = 3
          return value.toFixed(precision)
        },
      },
    },
    series: [
      {
        name: '历史走势',
        type: 'line',
        data: [...historicalValues, ...new Array(predictDates.length).fill(null)],
        lineStyle: { color: chartColors.historical, width: 2 },
        itemStyle: { color: chartColors.historical },
        symbol: 'circle',
        symbolSize: 4,
      },
      {
        name: '预测走势',
        type: 'line',
        data: predictValues,
        lineStyle: { color: chartColors.predicted, width: 2, type: 'dashed' },
        itemStyle: { color: chartColors.predicted },
        symbol: 'circle',
        symbolSize: 4,
      },
      {
        name: '置信区间',
        type: 'line',
        data: upperValues,
        lineStyle: { opacity: 0 },
        symbol: 'none',
        areaStyle: { color: chartColors.confidence },
        z: 1,
      },
      {
        name: '置信区间下界',
        type: 'line',
        data: lowerValues,
        lineStyle: { opacity: 0 },
        symbol: 'none',
        areaStyle: { color: '#fff' },
        z: 2,
      },
    ],
  }

  return option
}

/* ==== 雷达图选项构建 ==== */

export const useRadarChart = (scoreData: RadarScoreData[]) => {
  const indicators: RadarIndicator[] = [
    { name: '基本面', max: 5 },
    { name: '技术面', max: 5 },
    { name: '风险', max: 5 },
    { name: '成本', max: 5 },
    { name: '情绪', max: 5 },
  ]

  const seriesData = scoreData.map((item, index) => ({
    name: item.name,
    value: item.value,
    itemStyle: { color: chartColors.radar[index % chartColors.radar.length] },
    areaStyle: { opacity: 0.1 },
  }))

  const option: ECOption = {
    ...defaultChartOptions,
    tooltip: { trigger: 'item', confine: true },
    legend: {
      data: scoreData.map(item => item.name),
      right: 10,
      top: 'center',
      orient: 'vertical',
    },
    radar: {
      indicator: indicators,
      center: ['50%', '50%'],
      radius: '60%',
      axisName: { color: '#333', fontSize: 14, fontWeight: 'bold' },
      splitNumber: 5,
      axisLine: { lineStyle: { color: '#ddd' } },
      splitLine: { lineStyle: { color: '#ddd' } },
      splitArea: { areaStyle: { color: ['#fff', '#f5f5f5'] } },
    },
    series: [
      {
        type: 'radar',
        data: seriesData,
        emphasis: { lineStyle: { width: 3 } },
      },
    ],
  }

  return option
}

/* ==== 响应式图表管理 ==== */

export const useChartManager = () => {
  const chartId = ref<string>('')
  const chartRef = ref<any>(null)

  /** 初始化图表（异步：首次加载 ECharts 核心） */
  const init = async (container: HTMLElement, options?: ECOption) => {
    const result = await initChart(container, options)
    chartId.value = result.id
    chartRef.value = result.chart
    return result
  }

  /** 更新图表（同步） */
  const update = (options: ECOption) => {
    if (chartId.value) {
      updateChart(chartId.value, options)
    }
  }

  /** 调整大小（同步） */
  const resize = () => {
    if (chartId.value) {
      resizeChart(chartId.value)
    }
  }

  /** 销毁图表（同步） */
  const dispose = () => {
    if (chartId.value) {
      disposeChart(chartId.value)
      chartId.value = ''
      chartRef.value = null
    }
  }

  onUnmounted(() => {
    dispose()
  })

  return { chartId, chartRef, init, update, resize, dispose }
}
