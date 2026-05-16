const INDUSTRY_COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899']

function lightenColor(hex: string, factor: number = 0.4): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  const nr = Math.round(r + (255 - r) * factor)
  const ng = Math.round(g + (255 - g) * factor)
  const nb = Math.round(b + (255 - b) * factor)
  return `#${nr.toString(16).padStart(2, '0')}${ng.toString(16).padStart(2, '0')}${nb.toString(16).padStart(2, '0')}`
}

export function useSunburstChart() {
  function buildSunburstOption(
    data: Array<{ industry: string; stocks: Array<{ name: string; value: number }> }>
  ): Record<string, any> {
    const seriesData = data.map((item, index) => {
      const color = INDUSTRY_COLORS[index % INDUSTRY_COLORS.length] ?? '#3B82F6'
      return {
        name: item.industry,
        itemStyle: { color },
        children: item.stocks.map(stock => ({
          name: stock.name,
          value: stock.value,
          itemStyle: { color: lightenColor(color) },
        })),
      }
    })

    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        confine: true,
        formatter: (params: any) => {
          const path = params.treePathInfo
            ?.map((node: any) => node.name)
            .filter(Boolean)
            .join(' > ')
          return `${path}<br/>${params.marker} ${params.name}: ${params.value}`
        },
      },
      series: [
        {
          type: 'sunburst',
          data: seriesData,
          radius: ['15%', '75%'],
          sort: undefined,
          emphasis: { focus: 'ancestor' },
          levels: [
            {},
            {
              r0: '15%',
              r: '45%',
              label: {
                show: true,
                rotate: 'tangential',
                fontSize: 12,
                fontWeight: 500,
                color: '#fff',
              },
              itemStyle: { borderWidth: 2, borderColor: '#fff' },
            },
            {
              r0: '45%',
              r: '75%',
              label: { show: false },
              itemStyle: { borderWidth: 1, borderColor: '#fff' },
            },
          ],
        },
      ],
    }
  }

  return { buildSunburstOption }
}
