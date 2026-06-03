export function usePercentileChart() {
  function getBarColor(percentile: number): string {
    if (percentile <= 25) return '#EF4444'
    if (percentile <= 75) return '#F59E0B'
    return '#10B981'
  }

  function buildPercentileOption(params: {
    items: Array<{ name: string; value: number; percentile: number }>
  }): Record<string, any> {
    const { items } = params

    const names = items.map(item => item.name)
    const values = items.map(item => item.value)
    const percentiles = items.map(item => item.percentile)
    const colors = items.map(item => getBarColor(item.percentile))

    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        confine: true,
        formatter: (params: any[]) => {
          const item = params?.[0]
          if (!item) return ''
          const idx = item.dataIndex
          const data = items[idx]
          return data ? `${data.name}<br/>数值: ${data.value}<br/>百分位: ${data.percentile}%` : ''
        },
      },
      grid: {
        left: '3%',
        right: '12%',
        top: '5%',
        bottom: '5%',
        containLabel: true,
      },
      xAxis: {
        type: 'value',
        show: false,
        max: 100,
      },
      yAxis: {
        type: 'category',
        data: names,
        inverse: true,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          color: '#333',
          fontSize: 13,
          fontWeight: 500,
        },
      },
      series: [
        {
          type: 'bar',
          data: percentiles.map((p, i) => ({
            value: p,
            itemStyle: {
              color: colors[i],
              borderRadius: [0, 4, 4, 0],
            },
          })),
          barWidth: 18,
          label: {
            show: true,
            position: 'insideLeft',
            formatter: (params: any) => {
              const idx = params?.dataIndex
              if (idx == null) return ''
              return `${items[idx]?.value ?? ''}`
            },
            color: '#fff',
            fontSize: 12,
            fontWeight: 600,
            fontFamily: 'JetBrains Mono',
          },
          z: 2,
        },
        {
          type: 'bar',
          data: percentiles.map(() => 100),
          barWidth: 18,
          itemStyle: {
            color: 'rgba(0,0,0,0.04)',
            borderRadius: [0, 4, 4, 0],
          },
          label: {
            show: true,
            position: 'right',
            formatter: (params: any) => {
              const idx = params?.dataIndex
              if (idx == null) return ''
              return `Top ${items[idx]?.percentile ?? 0}%`
            },
            color: '#666',
            fontSize: 12,
            fontFamily: 'JetBrains Mono',
          },
          z: 1,
          silent: true,
          animation: false,
        },
      ],
    }
  }

  return { buildPercentileOption }
}
