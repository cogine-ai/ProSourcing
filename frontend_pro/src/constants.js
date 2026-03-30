/**
 * 任务状态常量定义 (CodeRabbit 建议优化)
 * 作用：统一前后端状态标识，避免硬编码字符串导致的拼写错误。
 */
export const TASK_STATUS = {
  PENDING: 'pending',        // 待处理
  SCRAPING: 'scraping',      // 抓取中
  COMPLETED: 'completed',    // 已完成
  FAILED: 'failed',          // 失败
  RETRYING: 'retrying'       // 重试中
};

export const CATEGORY_TYPES = {
  SEARCH: 'search',
  CATEGORY: 'category'
};
