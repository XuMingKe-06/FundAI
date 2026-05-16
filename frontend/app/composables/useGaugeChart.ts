export function useGaugeChart() {
  function buildGaugeOption(params: {
    value: number
    max?: number
    label?: string
    detail?: string
  }): Record<string, any> {
    const { value, max = 5, label = '综合评分', detail } = params

    return {
      backgroundColor: 'transparent',
      series: [
        {
          type: 'gauge',
          startAngle: 225,
          endAngle: -45,
          min: 0,
          max,
          splitNumber: 5,
          progress: {
            show: true,
            width: 12,
          },
          axisLine: {
            lineStyle: {
              width: 12,
              color: [
                [0.4, '#EF4444'],
                [0.7, '#F59E0B'],
                [1, '#10B981'],
              ],
            },
          },
          pointer: {
            length: '60%',
            width: 6,
          },
          axisTick: {
            distance: -18,
            length: 6,
            lineStyle: {
              color: '#999',
              width: 1,
            },
          },
          splitLine: {
            distance: -22,
            length: 12,
            lineStyle: {
              color: '#999',
              width: 1,
            },
          },
          axisLabel: {
            distance: -30,
            color: '#666',
            fontSize: 12,
          },
          anchor: {
            show: true,
            size: 12,
            showAbove: true,
            itemStyle: {
              borderWidth: 3,
              borderColor: '#10B981',
              color: '#fff',
            },
          },
          title: {
            show: true,
            offsetCenter: [0, '70%'],
            color: '#666',
            fontSize: 14,
          },
          detail: {
            valueAnimation: true,
            fontSize: 28,
            fontWeight: 'bold',
            fontFamily: 'JetBrains Mono',
            color: '#333',
            offsetCenter: [0, '40%'],
            formatter: `{value}`,
          },
          data: [
            {
              value,
              name: label,
            },
          ],
        },
      ],
    }
  }

  return { buildGaugeOption }
}
