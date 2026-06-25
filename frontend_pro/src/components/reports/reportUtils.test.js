import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
    buildReportPagination,
    getListedDays,
    sortTaskProducts,
} from './reportUtils.js';

describe('buildReportPagination', () => {
    it('returns empty array for non-positive total pages', () => {
        expect(buildReportPagination(1, 0)).toEqual([]);
        expect(buildReportPagination(1, -3)).toEqual([]);
        expect(buildReportPagination(1, NaN)).toEqual([]);
    });

    it('returns all page numbers when total pages is small', () => {
        expect(buildReportPagination(1, 5)).toEqual([1, 2, 3, 4, 5]);
    });

    it('clamps out-of-range current page', () => {
        expect(buildReportPagination(-5, 10)).toEqual([1, 2, 3, 4, 5, 'ellipsis-right', 10]);
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

    it('shows middle window for central pages', () => {
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
});

describe('getListedDays', () => {
    beforeEach(() => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2026-06-25T12:00:00Z'));
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('returns fallback for missing or invalid dates', () => {
        expect(getListedDays(null)).toBe(999);
        expect(getListedDays('')).toBe(999);
        expect(getListedDays('not-a-date')).toBe(999);
    });

    it('parses datetime strings with fractional seconds', () => {
        expect(getListedDays('2026-06-20 12:00:00.123456')).toBe(5);
    });

    it('returns at least one day for same-day listings', () => {
        expect(getListedDays('2026-06-25T10:00:00Z')).toBe(1);
    });
});

describe('sortTaskProducts', () => {
    const getMetricScore = () => 0;
    const selectedTask = { category_stats: { sale_qty: 0, sale_product_qty: 1 } };

    const makeProduct = (createdDt) => ({
        products_raw_data: { created_dt: createdDt, sale_qty: 0, review_qty: 0, sale_price: 0 },
    });

    beforeEach(() => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2026-06-25T12:00:00Z'));
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('sorts days_desc with longest-listed products first', () => {
        const older = makeProduct('2026-01-01T00:00:00Z');
        const newer = makeProduct('2026-06-01T00:00:00Z');
        const sorted = sortTaskProducts([newer, older], 'days_desc', getMetricScore, selectedTask);
        expect(sorted[0]).toBe(older);
        expect(sorted[1]).toBe(newer);
    });

    it('sorts days_asc with newest listings first', () => {
        const older = makeProduct('2026-01-01T00:00:00Z');
        const newer = makeProduct('2026-06-01T00:00:00Z');
        const sorted = sortTaskProducts([older, newer], 'days_asc', getMetricScore, selectedTask);
        expect(sorted[0]).toBe(newer);
        expect(sorted[1]).toBe(older);
    });
});
