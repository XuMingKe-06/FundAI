<template>
  <div class="report-export">
    <button
      class="report-export__btn report-export__btn--image"
      :disabled="exportingImage || !reportRef"
      @click="exportAsImage"
    >
      <svg v-if="!exportingImage" class="report-export__icon" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="2" y="2" width="12" height="12" rx="2" stroke="currentColor" stroke-width="1.5"/>
        <circle cx="5.5" cy="5.5" r="1.5" fill="currentColor"/>
        <path d="M2 11L5.5 7.5L8 10L10.5 7L14 11" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
      </svg>
      <span v-if="exportingImage" class="report-export__spinner"></span>
      <span>{{ exportingImage ? '导出中...' : '导出图片' }}</span>
    </button>
    <button
      class="report-export__btn report-export__btn--pdf"
      :disabled="exportingPdf || !reportRef"
      @click="exportAsPdf"
    >
      <svg v-if="!exportingPdf" class="report-export__icon" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M4 1H10L13 4V14C13 14.5523 12.5523 15 12 15H4C3.44772 15 3 14.5523 3 14V2C3 1.44772 3.44772 1 4 1Z" stroke="currentColor" stroke-width="1.5"/>
        <path d="M10 1V4H13" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
        <path d="M5 8H11M5 10.5H9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
      <span v-if="exportingPdf" class="report-export__spinner"></span>
      <span>{{ exportingPdf ? '导出中...' : '导出PDF' }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import html2canvas from 'html2canvas'
import { jsPDF } from 'jspdf'

const props = defineProps<{
  reportRef: HTMLElement | null
}>()

const exportingImage = ref(false)
const exportingPdf = ref(false)

async function exportAsImage() {
  if (!props.reportRef || exportingImage.value) return
  exportingImage.value = true
  try {
    const canvas = await html2canvas(props.reportRef, {
      scale: 2,
      useCORS: true,
      backgroundColor: null,
    })
    const link = document.createElement('a')
    link.download = `fund-report-${Date.now()}.png`
    link.href = canvas.toDataURL('image/png')
    link.click()
    ElMessage.success('图片导出成功')
  } catch (e) {
    ElMessage.error('图片导出失败，请重试')
  } finally {
    exportingImage.value = false
  }
}

async function exportAsPdf() {
  if (!props.reportRef || exportingPdf.value) return
  exportingPdf.value = true
  try {
    const canvas = await html2canvas(props.reportRef, {
      scale: 2,
      useCORS: true,
      backgroundColor: null,
    })
    const imgData = canvas.toDataURL('image/png')
    const imgWidth = canvas.width
    const imgHeight = canvas.height
    const pdf = new jsPDF({
      orientation: imgWidth > imgHeight ? 'landscape' : 'portrait',
      unit: 'px',
      format: [imgWidth, imgHeight],
    })
    pdf.addImage(imgData, 'PNG', 0, 0, imgWidth, imgHeight)
    pdf.save(`fund-report-${Date.now()}.pdf`)
    ElMessage.success('PDF导出成功')
  } catch (e) {
    ElMessage.error('PDF导出失败，请重试')
  } finally {
    exportingPdf.value = false
  }
}
</script>

<style scoped>
.report-export {
  display: flex;
  gap: var(--space-2);
}

.report-export__btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  border: 1px solid var(--border-base);
  border-radius: var(--radius-base);
  background: var(--bg-elevated);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
  line-height: var(--leading-normal);
}

.report-export__btn:hover:not(:disabled) {
  border-color: var(--color-primary-300);
  color: var(--color-primary-500);
  background: var(--color-primary-50);
}

.report-export__btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.report-export__btn--image:hover:not(:disabled) {
  border-color: var(--color-primary-300);
  color: var(--color-primary-500);
  background: var(--color-primary-50);
}

.report-export__btn--pdf:hover:not(:disabled) {
  border-color: var(--color-danger-100);
  color: var(--color-danger-500);
  background: var(--color-danger-50);
}

.report-export__icon {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.report-export__spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--border-base);
  border-top-color: var(--color-primary-500);
  border-radius: var(--radius-full);
  animation: spin 0.6s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
