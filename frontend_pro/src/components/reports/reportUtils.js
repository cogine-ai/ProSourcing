export const anyCyrillic = (str) => /[\u0400-\u04FF]/.test(str);

const safeParseJsonString = (value, fallback) => {
    if (typeof value !== 'string') return fallback;

    const text = value.trim();
    if (!text || (text[0] !== '{' && text[0] !== '[')) {
        return fallback;
    }

    try {
        return JSON.parse(text);
    } catch {
        return fallback;
    }
};

const normalizeCategoryLookupKey = (value) => String(value || '').trim().toLowerCase();

const extractCategoryCandidates = (cat) => {
    if (!cat) return [];

    const candidates = new Set();
    const push = (value) => {
        if (!value && value !== 0) return;
        const text = String(value).trim();
        if (!text) return;
        candidates.add(text);
    };

    [
        cat?.name_ru,
        cat?.category_name,
        cat?.category,
        cat?.name,
        cat?.title,
        cat?.category_code,
        cat?.category_id,
        cat?.algatop_id,
        cat?.id,
    ].forEach(push);

    const fullName = cat?.category_name || cat?.category || cat?.name || cat?.title || '';
    if (fullName) {
        push(fullName.split(' - ')[0]);
        push(fullName.replace(/\s*\(.*?\)\s*/g, '').trim());

        if (fullName.startsWith('RPA采集_')) {
            const parts = fullName.split('_');
            if (parts.length > 1) {
                push(parts[1]);
                push(parts[1].replace(/\(.*?\)/g, '').trim());
            }
        }
    }

    return Array.from(candidates);
};

export const buildCategoryNameLookup = (nodes = []) => {
    const lookup = new Map();

    const walk = (nodeList) => {
        nodeList.forEach((node) => {
            if (!node) return;

            const zhName = node?.name_cn || node?.category_name_cn || node?.category_cn;
            if (zhName && !anyCyrillic(zhName)) {
                extractCategoryCandidates(node).forEach((candidate) => {
                    lookup.set(normalizeCategoryLookupKey(candidate), zhName);
                });
            }

            if (Array.isArray(node?.children) && node.children.length > 0) {
                walk(node.children);
            }
        });
    };

    walk(Array.isArray(nodes) ? nodes : []);
    return lookup;
};

const resolveCategoryZhName = (cat, categoryLookup = new Map()) => {
    const candidates = typeof cat === 'string' ? [cat] : extractCategoryCandidates(cat);
    for (const candidate of candidates) {
        const match = categoryLookup.get(normalizeCategoryLookupKey(candidate));
        if (match) return match;
    }
    return '';
};

export const getCategoryDisplayName = (cat, categoryLookup = new Map()) => {
    if (!cat) return '未知品类';

    const cnName = cat?.name_cn || cat?.category_name_cn || cat?.category_cn;
    if (cnName && !anyCyrillic(cnName)) return cnName;

    const fullName = cat?.category_name || cat?.category || cat?.name || '';
    const match = fullName.match(/\((.*?)\)/);
    if (match) return match[1];

    const treeMatchedName = resolveCategoryZhName(cat, categoryLookup);
    if (treeMatchedName) return treeMatchedName;

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

export const getTopCategoryZhLabel = (task, categories = [], categoryLookup = new Map()) => {
    if (task?.top_category_name_cn) return task.top_category_name_cn;
    if (task?.top_category_label) return task.top_category_label;

    const normalizedUpCategories = Array.isArray(task?.up_categories)
        ? task.up_categories
        : (typeof task?.up_categories === 'string'
            ? (() => {
                const parsed = safeParseJsonString(task.up_categories, []);
                return Array.isArray(parsed) ? parsed : [];
            })()
            : []);

    const topCat = normalizedUpCategories[0];
    if (!topCat) return '一级分类';

    const direct = getCategoryDisplayName(topCat, categoryLookup);
    if (direct && /[\u4e00-\u9fff]/.test(direct)) return direct;

    const topRu = typeof topCat === 'string' ? topCat : (topCat?.name_ru || topCat?.category_name || topCat?.name || '');
    const match = categories.find((c) => (c?.name_ru || c?.category_name || c?.name || '') === topRu);
    return match?.name_cn || resolveCategoryZhName(topCat, categoryLookup) || direct || '一级分类';
};

export const buildReportPagination = (currentPage, totalPages) => {
    const total = Number(totalPages);
    if (!Number.isFinite(total) || Math.floor(total) <= 0) return [];

    const page = Number(currentPage);
    const safeTotalPages = Math.floor(total);
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

export const parsePreviewImage = (previewImageList, size = 'medium') => {
    if (!previewImageList) return '';

    try {
        const parsed = typeof previewImageList === 'string'
            ? safeParseJsonString(previewImageList, null)
            : previewImageList;
        const item = Array.isArray(parsed) ? parsed[0] : parsed;
        return item?.[size] || item?.medium || '';
    } catch {
        return '';
    }
};
