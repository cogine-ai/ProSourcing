import { afterEach, describe, expect, it, vi } from 'vitest';
import {
    anyCyrillic,
    buildReportPagination,
    buildCategoryNameLookup,
    getCategoryDisplayName,
    getListedDays,
    getTaskDurationLabel,
    getTopCategoryZhLabel,
    isHighQualityProduct,
    parsePreviewImage,
    sortTaskProducts,
} from './reportUtils.js';

const forceNum = (value) => {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : 0;
};

describe('buildReportPagination', () => {
    it('returns empty array for invalid totals', () => {
        expect(buildReportPagination(1, 0)).toEqual([]);
        expect(buildReportPagination(1, -3)).toEqual([]);
        expect(buildReportPagination(1, Number.NaN)).toEqual([]);
    });

    it('returns all page numbers when total pages is small', () => {
        expect(buildReportPagination(2, 5)).toEqual([1, 2, 3, 4, 5]);
    });

    it('clamps current page to the last page for trailing windows', () => {
        expect(buildReportPagination(99, 10)).toEqual([
            1,
            'ellipsis-left',
            6,
            7,
            8,
            9,
            10,
        ]);
    });

    it('shows a middle ellipsis window for interior pages', () => {
        expect(buildReportPagination(5, 10)).toEqual([
            1,
            'ellipsis-left',
            4,
            5,
            6,
            'ellipsis-right',
            10,
        ]);
    });

    it('shows trailing ellipsis window near the end', () => {
        expect(buildReportPagination(9, 10)).toEqual([
            1,
            'ellipsis-left',
            6,
            7,
            8,
            9,
            10,
        ]);
    });
});

describe('getListedDays', () => {
    afterEach(() => {
        vi.useRealTimers();
    });

    it('returns fallback for missing or invalid dates', () => {
        expect(getListedDays(null)).toBe(999);
        expect(getListedDays('not-a-date')).toBe(999);
    });

    it('parses dotted datetime strings and counts whole days', () => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2026-05-30T12:00:00Z'));

        expect(getListedDays('2026-05-20 10:00:00.000')).toBe(10);
    });
});

describe('sortTaskProducts listed-day ordering', () => {
    afterEach(() => {
        vi.useRealTimers();
    });

    const older = { products_raw_data: { created_dt: '2026-01-01T00:00:00' } };
    const newer = { products_raw_data: { created_dt: '2026-05-01T00:00:00' } };
    const scoreStub = () => 0;

    it('sorts days_desc with older listings first', () => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2026-05-30T00:00:00Z'));

        const sorted = sortTaskProducts([newer, older], 'days_desc', scoreStub, null);
        expect(sorted[0]).toBe(older);
        expect(sorted[1]).toBe(newer);
    });

    it('sorts days_asc with newer listings first', () => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2026-05-30T00:00:00Z'));

        const sorted = sortTaskProducts([older, newer], 'days_asc', scoreStub, null);
        expect(sorted[0]).toBe(newer);
        expect(sorted[1]).toBe(older);
    });
});

describe('getTaskDurationLabel', () => {
    it('prefers explicit duration and guards invalid ranges', () => {
        expect(getTaskDurationLabel({ duration: '3m 4s' })).toBe('3m 4s');
        expect(getTaskDurationLabel({ created_at: '2026-05-30T10:00:00', finished_at: '2026-05-30T09:00:00' })).toBe('--');
        expect(getTaskDurationLabel({ created_at: '2026-05-30T10:00:00', finished_at: '2026-05-30T10:02:05' })).toBe('2m 5s');
    });
});

describe('category display helpers', () => {
    it('detects cyrillic text', () => {
        expect(anyCyrillic('Телефоны')).toBe(true);
        expect(anyCyrillic('手机')).toBe(false);
    });

    it('builds lookup keys from nested category nodes', () => {
        const lookup = buildCategoryNameLookup([
            {
                name_cn: '手机',
                name_ru: 'Телефоны',
                children: [{ name_cn: '配件', category_name: 'Accessories (配件)' }],
            },
        ]);

        expect(lookup.get('телефоны')).toBe('手机');
        expect(lookup.get('accessories')).toBe('配件');
    });

    it('resolves Chinese labels from parentheses and tree lookup', () => {
        expect(getCategoryDisplayName({ category_name: 'Phones (手机)' })).toBe('手机');

        const lookup = buildCategoryNameLookup([{ name_cn: '无人机', name_ru: 'Drones' }]);
        expect(getCategoryDisplayName({ name_ru: 'Drones' }, lookup)).toBe('无人机');
    });

    it('parses up_categories JSON strings for top labels', () => {
        const task = {
            up_categories: JSON.stringify([{ category_name: 'Phones (手机)' }]),
        };
        expect(getTopCategoryZhLabel(task)).toBe('手机');
    });
});

describe('product filtering helpers', () => {
    afterEach(() => {
        vi.useRealTimers();
    });

    it('filters high-quality products using numeric thresholds', () => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2026-05-30T00:00:00Z'));

        const raw = {
            created_dt: '2026-05-20T00:00:00',
            sale_qty: 120,
            review_qty: 40,
            sale_price: 9000,
        };

        expect(isHighQualityProduct(raw, { filterDays: 30, filterSales: 100, filterReviews: 20, filterMinPrice: 5000 }, forceNum)).toBe(true);
        expect(isHighQualityProduct(raw, { filterDays: 5, filterSales: 100, filterReviews: 20, filterMinPrice: 5000 }, forceNum)).toBe(false);
    });

    it('parses preview image JSON safely', () => {
        const payload = JSON.stringify([{ medium: 'https://example.com/m.jpg', large: 'https://example.com/l.jpg' }]);
        expect(parsePreviewImage(payload, 'large')).toBe('https://example.com/l.jpg');
        expect(parsePreviewImage('not-json')).toBe('');
    });
});
