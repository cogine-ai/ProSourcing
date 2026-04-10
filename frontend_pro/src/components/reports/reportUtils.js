export const anyCyrillic = (str) => /[\u0400-\u04FF]/.test(str);
const DEFAULT_LISTED_DAYS_FALLBACK = 999;

const forceIntFallback = (value) => {
    if (value === null || value === undefined || value === '') return 0;
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : 0;
};

export const getCategoryDisplayName = (cat) => {
    if (!cat) return "未知品类";

    const cnName = cat?.name_cn || cat?.category_name_cn || cat?.category_cn;
    if (cnName && !anyCyrillic(cnName)) return cnName;

    const fullName = cat?.category_name || cat?.category || cat?.name || "";
    const match = fullName.match(/\((.*?)\)/);
    if (match) return match[1];

    if (fullName.startsWith('RPA采集_')) {
        const parts = fullName.split('_');
        if (parts.length > 1) {
            const subMatch = parts[1].match(/\((.*?)\)/);
            if (subMatch) return subMatch[1];
            return parts[1];
        }
    }

    return fullName.split(' - ')[0];
};

export const getTopCategoryZhLabel = (task, categories = []) => {
    if (task?.top_category_name_cn) return task.top_category_name_cn;
    if (task?.top_category_label) return task.top_category_label;

    const normalizedUpCategories = Array.isArray(task?.up_categories)
        ? task.up_categories
        : (typeof task?.up_categories === 'string'
            ? (() => {
                try {
                    const parsed = JSON.parse(task.up_categories);
                    return Array.isArray(parsed) ? parsed : [];
                } catch {
                    return [];
                }
            })()
            : []);

    const topCat = normalizedUpCategories[0];
    if (!topCat) return '一级分类';

    const direct = getCategoryDisplayName(topCat);
    if (direct && /[\u4e00-\u9fff]/.test(direct)) return direct;

    const topRu = typeof topCat === 'string' ? topCat : (topCat?.name_ru || topCat?.category_name || topCat?.name || '');
    const match = categories.find((c) => (c?.name_ru || c?.category_name || c?.name || '') === topRu);
    return match?.name_cn || direct || '一级分类';
};

export const buildReportPagination = (currentPage, totalPages) => {
    const total = Number(totalPages);
    const page = Number(currentPage);
    const safeTotalPages = Number.isFinite(total) ? Math.max(1, Math.floor(total)) : 1;
    const safeCurrentPage = Number.isFinite(page)
        ? Math.min(safeTotalPages, Math.max(1, Math.floor(page)))
        : 1;

    if (safeTotalPages <= 7) {
        return Array.from({ length: safeTotalPages }, (_, index) => index + 1);
    }

    if (safeCurrentPage <= 4) {
        return [1, 2, 3, 4, 5, 'ellipsis-right', safeTotalPages];
    }

    if (safeCurrentPage >= safeTotalPages - 3) {
        return [1, 'ellipsis-left', safeTotalPages - 4, safeTotalPages - 3, safeTotalPages - 2, safeTotalPages - 1, safeTotalPages];
    }

    return [1, 'ellipsis-left', safeCurrentPage - 1, safeCurrentPage, safeCurrentPage + 1, 'ellipsis-right', safeTotalPages];
};

export const getListedDays = (createdDt) => (
    createdDt
        ? Math.max(1, Math.floor((new Date() - new Date(createdDt.split('.')[0].replace(' ', 'T'))) / (1000 * 60 * 60 * 24)))
        : DEFAULT_LISTED_DAYS_FALLBACK
);

export const getTaskDurationLabel = (task) => {
    if (task?.duration) return task.duration;
    if (!task?.created_at || !task?.finished_at) return '--';

    const start = new Date(task.created_at);
    const end = new Date(task.finished_at);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || end < start) return '--';

    const diff = Math.floor((end - start) / 1000);
    const minutes = Math.floor(diff / 60);
    const seconds = diff % 60;
    return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
};

export const isHighQualityProduct = (raw, filters, forceNum) => {
    const listedDays = getListedDays(raw.created_dt);
    return listedDays <= forceNum(filters.filterDays)
        && forceNum(raw.sale_qty) >= forceNum(filters.filterSales)
        && forceNum(raw.review_qty) >= forceNum(filters.filterReviews)
        && forceNum(raw.sale_price) >= forceNum(filters.filterMinPrice);
};

export const filterTaskProducts = (taskProducts, onlyHighQuality, filters, forceNum) => (
    taskProducts.filter((tp) => {
        if (!onlyHighQuality) return true;
        return isHighQualityProduct(tp.products_raw_data, filters, forceNum);
    })
);

export const getAverageSalesPerProduct = (selectedTask) => {
    const saleQty = forceIntFallback(selectedTask?.category_stats?.sale_qty);
    const productQty = forceIntFallback(selectedTask?.category_stats?.sale_product_qty);
    if (productQty <= 0) return 0;
    return saleQty / productQty;
};

export const getTaskProductScore = (tp, getMetricScore, selectedTask) => {
    const raw = tp.products_raw_data;
    const listedDays = getListedDays(raw.created_dt);
    const avgSales = getAverageSalesPerProduct(selectedTask);
    return getMetricScore('monthly_sales', raw.sale_qty || 0)
        + getMetricScore('reviews', raw.review_qty || 0)
        + getMetricScore('price', raw.sale_price || 0)
        + getMetricScore('days_per_review', listedDays, raw.review_qty || 0)
        + getMetricScore('avg_sales', avgSales);
};

export const sortTaskProducts = (taskProducts, sortBy, getMetricScore, selectedTask) => (
    [...taskProducts].sort((a, b) => {
        const ra = a.products_raw_data;
        const rb = b.products_raw_data;

        switch (sortBy) {
            case 'amount':
                return (rb.sale_amount || 0) - (ra.sale_amount || 0);
            case 'sales':
                return (rb.sale_qty || 0) - (ra.sale_qty || 0);
            case 'price_asc':
                return (ra.sale_price || 0) - (rb.sale_price || 0);
            case 'reviews':
                return (rb.review_qty || 0) - (ra.review_qty || 0);
            case 'days_desc':
                return getListedDays(ra.created_dt) - getListedDays(rb.created_dt);
            case 'days_asc':
                return getListedDays(rb.created_dt) - getListedDays(ra.created_dt);
            case 'score':
            default:
                return getTaskProductScore(b, getMetricScore, selectedTask) - getTaskProductScore(a, getMetricScore, selectedTask);
        }
    })
);

export const parsePreviewImage = (previewImageList, size = 'medium') => {
    if (!previewImageList) return '';

    try {
        const parsed = typeof previewImageList === 'string' ? JSON.parse(previewImageList) : previewImageList;
        const item = Array.isArray(parsed) ? parsed[0] : parsed;
        return item?.[size] || item?.medium || '';
    } catch {
        return '';
    }
};
