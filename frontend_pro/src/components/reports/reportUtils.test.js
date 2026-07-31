import { describe, expect, it, vi, afterEach } from 'vitest';
import {
    buildReportPagination,
    getCategoryDisplayName,
    getListedDays,
    sortTaskProducts,
} from './reportUtils.js';

describe('buildReportPagination', () => {
    it('returns empty array for invalid totals', () => {
        expect(buildReportPagination(1, 0)).toEqual([]);
        expect(buildReportPagination(1, -3)).toEqual([]);
        expect(buildReportPagination(1, Number.NaN)).toEqual([]);
    });

    it('clamps current page into valid range', () => {
        expect(buildReportPagination(99, 5)).toEqual([1, 2, 3, 4, 5]);
        expect(buildReportPagination(-2, 5)).toEqual([1, 2, 3, 4, 5]);
    });

    it('builds leading window for early pages', () => {
        expect(buildReportPagination(2, 10)).toEqual([1, 2, 3, 4, 5, 'ellipsis-right', 10]);
    });

    it('builds trailing window for late pages', () => {
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

    it('returns fallback when date is missing or invalid', () => {
        expect(getListedDays(null)).toBe(999);
        expect(getListedDays('')).toBe(999);
        expect(getListedDays('not-a-date')).toBe(999);
    });

    it('parses datetime strings with fractional seconds', () => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2026-06-12T12:00:00Z'));

        expect(getListedDays('2026-06-10 12:00:00.123')).toBe(2);
    });

    it('never returns less than one day for valid timestamps', () => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2026-06-12T12:00:00Z'));

        expect(getListedDays('2026-06-12T11:30:00Z')).toBe(1);
    });
});

describe('sortTaskProducts day sorting', () => {
    const getMetricScore = () => 0;
    const selectedTask = { category_stats: { sale_qty: 0, sale_product_qty: 1 } };

    const products = [
        { products_raw_data: { created_dt: '2026-01-01' } },
        { products_raw_data: { created_dt: '2026-06-01' } },
        { products_raw_data: { created_dt: '2026-03-01' } },
    ];

    it('sorts days_desc from newest listed to oldest', () => {
        const sorted = sortTaskProducts(products, 'days_desc', getMetricScore, selectedTask);
        const dates = sorted.map((item) => item.products_raw_data.created_dt);
        expect(dates).toEqual(['2026-01-01', '2026-03-01', '2026-06-01']);
    });

    it('sorts days_asc from oldest listed to newest', () => {
        const sorted = sortTaskProducts(products, 'days_asc', getMetricScore, selectedTask);
        const dates = sorted.map((item) => item.products_raw_data.created_dt);
        expect(dates).toEqual(['2026-06-01', '2026-03-01', '2026-01-01']);
    });
});

describe('getCategoryDisplayName', () => {
    it('prefers non-cyrillic Chinese labels', () => {
        expect(getCategoryDisplayName({ name_cn: '手机' })).toBe('手机');
    });

    it('extracts parenthetical translation', () => {
        expect(getCategoryDisplayName({ category_name: 'Phones (手机)' })).toBe('手机');
    });
});
