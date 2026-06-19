export type ColorMode = 'china' | 'international'

const COLOR_MODE_KEY = 'fundai-color-mode'

export function useTheme() {
  const colorMode = ref<ColorMode>('china')

  function applyColorMode(mode: ColorMode) {
    if (import.meta.client) {
      if (mode === 'international') {
        document.documentElement.setAttribute('data-color-mode', 'international')
      } else {
        document.documentElement.removeAttribute('data-color-mode')
      }
    }
  }

  function setColorMode(mode: ColorMode) {
    colorMode.value = mode
    applyColorMode(mode)
    if (import.meta.client) {
      localStorage.setItem(COLOR_MODE_KEY, mode)
    }
  }

  function toggleColorMode() {
    setColorMode(colorMode.value === 'china' ? 'international' : 'china')
  }

  function initTheme() {
    if (!import.meta.client) return

    const savedColorMode = localStorage.getItem(COLOR_MODE_KEY) as ColorMode | null
    const initialColorMode = savedColorMode || 'china'

    colorMode.value = initialColorMode
    applyColorMode(initialColorMode)
  }

  const isInternationalColor = computed(() => colorMode.value === 'international')

  return {
    colorMode: readonly(colorMode),
    isInternationalColor,
    setColorMode,
    toggleColorMode,
    initTheme,
  }
}
