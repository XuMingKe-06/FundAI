const DEFAULT_COLOR = '#3B82F6'

function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

export function useAreaChart() {
  function buildAreaOption(params: {
    dates: string[]
    values: number[]
    label: string
    color?: string
  }): Record<string, any> {
    const { dates, values, label, color = DEFAULT_COLOR } = params

    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        confine: true,
        formatter: (params: any[]) => {
          const item = params[0]
          return `<div style="font-weight:bold">${item.axisValue}</div>${item.marker} ${label}: ${item.value.toFixed(2)}`
        },
      },
      grid: {
        left: '5%',
        right: '5%',
        top: '10%',
        bottom: '15%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: dates,
        boundaryGap: false,
        axisLabel: {
          rotate: dates.length > 12 ? 45 : 0,
          fontSize: 11,
        },
        axisLine: { lineStyle: { color: '#ddd' } },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { type: 'dashed', color: '#eee' } },
        axisLabel: { fontSize: 11 },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      series: [
        {
          name: label,
          type: 'line',
          data: values,
          smooth: 'monotone',
          symbol: 'none',
          lineStyle: { color, width: 2 },
          itemStyle: { color },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: hexToRgba(color, 0.3) },
                { offset: 1, color: hexToRgba(color, 0) },
              ],
            },
          },
        },
      ],
    }
  }

  return { buildAreaOption }
}
