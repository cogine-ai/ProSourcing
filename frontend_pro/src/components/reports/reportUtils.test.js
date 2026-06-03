import { afterEach, describe, expect, it, vi } from 'vitest';
import {
    buildReportPagination,
    getCategoryDisplayName,
    getListedDays,
    sortTaskProducts,
} from './reportUtils';

describe('buildReportPagination', () => {
    it('returns empty array for invalid totals', () => {
        expect(buildReportPagination(1, 0)).toEqual([]);
        expect(buildReportPagination(1, -3)).toEqual([]);
        expect(buildReportPagination(1, Number.NaN)).toEqual([]);
    });

    it('clamps the current page into range', () => {
        expect(buildReportPagination(99, 5)).toEqual([1, 2, 3, 4, 5]);
        expect(buildReportPagination(-2, 5)).toEqual([1, 2, 3, 4, 5]);
        expect(buildReportPagination('3.9', 5)).toEqual([1, 2, 3, 4, 5]);
    });

    it('returns all pages when total is seven or fewer', () => {
        expect(buildReportPagination(2, 4)).toEqual([1, 2, 3, 4]);
    });

    it('builds leading and trailing ellipsis windows', () => {
        expect(buildReportPagination(2, 12)).toEqual([1, 2, 3, 4, 5, 'ellipsis-right', 12]);
        expect(buildReportPagination(11, 12)).toEqual([1, 'ellipsis-left', 8, 9, 10, 11, 12]);
        expect(buildReportPagination(6, 12)).toEqual([1, 'ellipsis-left', 5, 6, 7, 'ellipsis-right', 12]);
    });
});

describe('getListedDays', () => {
    afterEach(() => {
        vi.useRealTimers();
    });

    it('returns fallback for missing or invalid dates', () => {
        expect(getListedDays(null)).toBe(999);
        expect(getListedDays('')).toBe(999);
        expect(getListedDays('not-a-date')).toBe(999);
    });

    it('normalizes dotted timestamps and counts whole days', () => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2026-06-03T12:00:00Z'));

        expect(getListedDays('2026-06-01 10:00:00.123')).toBe(2);
        expect(getListedDays('2026-06-03T00:00:00')).toBe(1);
    });
});

describe('sortTaskProducts listed-day ordering', () => {
    const getMetricScore = () => 0;
    const selectedTask = { category_stats: { sale_qty: 0, sale_product_qty: 0 } };

    const makeProduct = (createdDt) => ({
        products_raw_data: { created_dt: createdDt },
    });

    it('sorts longer-listed products first for days_desc', () => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2026-06-10T00:00:00Z'));

        const sorted = sortTaskProducts(
            [makeProduct('2026-05-01'), makeProduct('2026-01-01')],
            'days_desc',
            getMetricScore,
            selectedTask,
        );

        expect(sorted[0].products_raw_data.created_dt).toBe('2026-01-01');
        expect(sorted[1].products_raw_data.created_dt).toBe('2026-05-01');
        vi.useRealTimers();
    });

    it('sorts shorter-listed products first for days_asc', () => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2026-06-10T00:00:00Z'));

        const sorted = sortTaskProducts(
            [makeProduct('2026-01-01'), makeProduct('2026-05-01')],
            'days_asc',
            getMetricScore,
            selectedTask,
        );

        expect(sorted[0].products_raw_data.created_dt).toBe('2026-05-01');
        expect(sorted[1].products_raw_data.created_dt).toBe('2026-01-01');
        vi.useRealTimers();
    });
});

describe('getCategoryDisplayName', () => {
    it('prefers non-cyrillic Chinese names from the record', () => {
        expect(getCategoryDisplayName({ name_cn: '宠物用品' })).toBe('宠物用品');
    });

    it('extracts parenthetical labels from RPA category names', () => {
        expect(getCategoryDisplayName({ category_name: 'RPA采集_宠物(猫砂)' })).toBe('猫砂');
    });
});
