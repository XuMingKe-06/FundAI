export type ThemeMode = 'light' | 'dark'
export type ColorMode = 'china' | 'international'

const THEME_KEY = 'fundai-theme'
const COLOR_MODE_KEY = 'fundai-color-mode'

export function useTheme() {
  const themeMode = ref<ThemeMode>('light')
  const colorMode = ref<ColorMode>('china')

  function applyTheme(mode: ThemeMode) {
    if (import.meta.client) {
      document.documentElement.setAttribute('data-theme', mode)
      if (mode === 'dark') {
        document.documentElement.classList.add('dark')
      } else {
        document.documentElement.classList.remove('dark')
      }
    }
  }

  function applyColorMode(mode: ColorMode) {
    if (import.meta.client) {
      if (mode === 'international') {
        document.documentElement.setAttribute('data-color-mode', 'international')
      } else {
        document.documentElement.removeAttribute('data-color-mode')
      }
    }
  }

  function setTheme(mode: ThemeMode) {
    themeMode.value = mode
    applyTheme(mode)
    if (import.meta.client) {
      localStorage.setItem(THEME_KEY, mode)
    }
  }

  function toggleTheme() {
    setTheme(themeMode.value === 'light' ? 'dark' : 'light')
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

    const savedTheme = localStorage.getItem(THEME_KEY) as ThemeMode | null
    const savedColorMode = localStorage.getItem(COLOR_MODE_KEY) as ColorMode | null

    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    const initialTheme = savedTheme || (prefersDark ? 'dark' : 'light')
    const initialColorMode = savedColorMode || 'china'

    themeMode.value = initialTheme
    colorMode.value = initialColorMode
    applyTheme(initialTheme)
    applyColorMode(initialColorMode)

    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
      if (!localStorage.getItem(THEME_KEY)) {
        setTheme(e.matches ? 'dark' : 'light')
      }
    })
  }

  const isDark = computed(() => themeMode.value === 'dark')
  const isInternationalColor = computed(() => colorMode.value === 'international')

  return {
    themeMode: readonly(themeMode),
    colorMode: readonly(colorMode),
    isDark,
    isInternationalColor,
    setTheme,
    toggleTheme,
    setColorMode,
    toggleColorMode,
    initTheme,
  }
}
