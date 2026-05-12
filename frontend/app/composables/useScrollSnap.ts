/* 滚动吸附功能的配置接口 */
interface ScrollSnapConfig {
  threshold: number
  debounceTime: number
  animationDuration: number
  wheelThreshold: number
}

/* 区域信息接口 */
interface SectionInfo {
  key: string
  name: string
}

/* 默认配置 */
const DEFAULT_CONFIG: ScrollSnapConfig = {
  threshold: 50,
  debounceTime: 800,
  animationDuration: 600,
  wheelThreshold: 30
}

/* 滚动吸附功能 composable */
export function useScrollSnap(sections: SectionInfo[], config: Partial<ScrollSnapConfig> = {}) {
  const mergedConfig = { ...DEFAULT_CONFIG, ...config }

  /* 响应式状态 */
  const currentSectionIndex = ref(0)
  const isScrolling = ref(false)
  const accumulatedDelta = ref(0)

  /* 内部状态 */
  let scrollTimeout: ReturnType<typeof setTimeout> | null = null
  let sectionElements: NodeListOf<Element> | null = null

  /* 更新当前区域 */
  const updateCurrentSection = () => {
    if (!sectionElements || sectionElements.length === 0) return

    const scrollTop = window.pageYOffset || document.documentElement.scrollTop
    const windowHeight = window.innerHeight

    for (let i = 0; i < sectionElements.length; i++) {
      const el = sectionElements[i] as HTMLElement
      if (!el) continue

      const rect = el.getBoundingClientRect()
      const sectionTop = rect.top + scrollTop
      const sectionBottom = sectionTop + rect.height
      const viewCenter = scrollTop + windowHeight / 2

      if (viewCenter >= sectionTop && viewCenter < sectionBottom) {
        if (currentSectionIndex.value !== i) {
          currentSectionIndex.value = i
        }
        break
      }
    }
  }

  /* 检查是否应该触发吸附 */
  const checkShouldSnap = (direction: number): boolean => {
    if (!sectionElements || sectionElements.length === 0) return false

    const currentSection = sectionElements[currentSectionIndex.value] as HTMLElement | undefined
    if (!currentSection) return false

    const rect = currentSection.getBoundingClientRect()
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop
    const windowHeight = window.innerHeight

    const sectionTop = rect.top + scrollTop
    const sectionBottom = sectionTop + rect.height
    const currentScrollTop = scrollTop
    const currentScrollBottom = currentScrollTop + windowHeight

    if (direction > 0) {
      /* 向下滚动，检查是否到达区域底部 */
      const distanceToBottom = sectionBottom - currentScrollBottom
      return distanceToBottom <= mergedConfig.threshold
    } else {
      /* 向上滚动，检查是否到达区域顶部 */
      const distanceToTop = currentScrollTop - sectionTop
      return distanceToTop <= mergedConfig.threshold
    }
  }

  /* 滚动到指定区域 */
  const scrollToSection = (index: number) => {
    if (isScrolling.value || !sectionElements || index < 0 || index >= sectionElements.length) return

    const targetSection = sectionElements[index] as HTMLElement
    if (!targetSection) return

    const targetPosition = targetSection.offsetTop

    isScrolling.value = true

    window.scrollTo({
      top: targetPosition,
      behavior: 'smooth'
    })

    currentSectionIndex.value = index

    setTimeout(() => {
      isScrolling.value = false
    }, mergedConfig.animationDuration)
  }

  /* 处理滚动事件 */
  const handleScroll = () => {
    if (scrollTimeout) {
      clearTimeout(scrollTimeout)
    }

    scrollTimeout = setTimeout(() => {
      updateCurrentSection()
    }, 100)
  }

  /* 处理滚轮事件 */
  const handleWheel = (e: WheelEvent) => {
    /* 如果正在滚动中，阻止默认行为 */
    if (isScrolling.value) {
      e.preventDefault()
      return
    }

    const delta = e.deltaY
    const absDelta = Math.abs(delta)

    /* 忽略太小的滚动 */
    if (absDelta < mergedConfig.wheelThreshold) return

    /* 累计滚动量 */
    accumulatedDelta.value += delta

    /* 判断是否需要触发区域切换 */
    if (Math.abs(accumulatedDelta.value) > mergedConfig.threshold) {
      const direction = accumulatedDelta.value > 0 ? 1 : -1

      /* 检查是否在边界位置 */
      const shouldSnap = checkShouldSnap(direction)

      /* 检查是否可以切换到下一个区域 */
      const nextIndex = currentSectionIndex.value + direction
      const canSwitch = nextIndex >= 0 && (sectionElements ? nextIndex < sectionElements.length : false)

      if (shouldSnap && canSwitch) {
        /* 在边界位置且可以切换到下一个区域 */
        e.preventDefault()
        accumulatedDelta.value = 0
        scrollToSection(nextIndex)
      } else {
        /* 不在边界位置或无法切换，允许正常滚动 */
        accumulatedDelta.value = 0
      }
    }
  }

  /* 初始化滚动吸附 */
  const initScrollSnap = () => {
    sectionElements = document.querySelectorAll('.scroll-section')
    if (sectionElements.length === 0) return

    window.addEventListener('scroll', handleScroll, { passive: true })
    window.addEventListener('wheel', handleWheel, { passive: false })

    updateCurrentSection()
  }

  /* 销毁滚动吸附 */
  const destroyScrollSnap = () => {
    window.removeEventListener('scroll', handleScroll)
    window.removeEventListener('wheel', handleWheel)

    if (scrollTimeout) {
      clearTimeout(scrollTimeout)
    }
  }

  return {
    currentSectionIndex,
    isScrolling,
    scrollToSection,
    initScrollSnap,
    destroyScrollSnap,
    updateCurrentSection
  }
}
