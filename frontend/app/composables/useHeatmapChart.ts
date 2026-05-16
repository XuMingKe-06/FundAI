export function useHeatmapChart() {
  function buildHeatmapOption(params: {
    xLabels: string[]
    yLabels: string[]
    data: Array<[number, number, number]>
  }): Record<string, any> {
    const { xLabels, yLabels, data } = params

    const values = data.map(d => d[2])
    const minVal = Math.min(...values)
    const maxVal = Math.max(...values)
    const absMax = Math.max(Math.abs(minVal), Math.abs(maxVal), 0.01)

    return {
      backgroundColor: 'transparent',
      tooltip: {
        confine: true,
        formatter: (params: any) => {
          const [xIdx, yIdx, val] = params.data
          return `${yLabels[yIdx]} / ${xLabels[xIdx]}<br/>${params.marker} ${val.toFixed(2)}`
        },
      },
      grid: {
        left: '10%',
        right: '12%',
        top: '5%',
        bottom: '15%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: xLabels,
        splitArea: { show: true },
        axisLabel: {
          rotate: xLabels.length > 6 ? 45 : 0,
          fontSize: 11,
        },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'category',
        data: yLabels,
        splitArea: { show: true },
        axisLabel: { fontSize: 11 },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      visualMap: {
        min: -absMax,
        max: absMax,
        calculable: true,
        orient: 'vertical',
        right: '2%',
        top: 'center',
        inRange: {
          color: ['#EF4444', '#FEE2E2', '#FFFFFF', '#D1FAE5', '#10B981'],
        },
        textStyle: { fontSize: 11 },
      },
      series: [
        {
          type: 'heatmap',
          data,
          label: {
            show: true,
            fontSize: 10,
            fontFamily: 'JetBrains Mono',
            formatter: (params: any) => params.data[2].toFixed(2),
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 6,
              shadowColor: 'rgba(0, 0, 0, 0.3)',
            },
          },
          itemStyle: { borderWidth: 1, borderColor: '#fff' },
        },
      ],
    }
  }

  return { buildHeatmapOption }
}
