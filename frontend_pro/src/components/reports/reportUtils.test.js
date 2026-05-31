import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
    buildReportPagination,
    getListedDays,
    sortTaskProducts,
} from './reportUtils.js';

describe('buildReportPagination', () => {
    it('returns empty array for non-positive totals', () => {
        assert.deepEqual(buildReportPagination(1, 0), []);
        assert.deepEqual(buildReportPagination(1, -3), []);
        assert.deepEqual(buildReportPagination(1, NaN), []);
    });

    it('returns all pages when total is small', () => {
        assert.deepEqual(buildReportPagination(2, 5), [1, 2, 3, 4, 5]);
    });

    it('clamps current page into valid range', () => {
        assert.deepEqual(
            buildReportPagination(999, 10),
            [1, 'ellipsis-left', 6, 7, 8, 9, 10],
        );
        assert.deepEqual(
            buildReportPagination(-5, 10),
            [1, 2, 3, 4, 5, 'ellipsis-right', 10],
        );
    });
});

describe('getListedDays', () => {
    it('returns fallback for missing or invalid dates', () => {
        assert.equal(getListedDays(null), 999);
        assert.equal(getListedDays(''), 999);
        assert.equal(getListedDays('not-a-date'), 999);
    });

    it('returns at least one day for valid timestamps', () => {
        const days = getListedDays('2020-01-01T00:00:00');
        assert.ok(Number.isFinite(days));
        assert.ok(days >= 1);
    });
});

describe('sortTaskProducts listed-day ordering', () => {
    const older = { products_raw_data: { created_dt: '2018-06-01T00:00:00' } };
    const newer = { products_raw_data: { created_dt: '2025-06-01T00:00:00' } };
    const scoreFn = () => 0;
    const task = {};

    it('sorts days_desc with longer-listed products first', () => {
        const sorted = sortTaskProducts([newer, older], 'days_desc', scoreFn, task);
        assert.equal(sorted[0], older);
        assert.equal(sorted[1], newer);
    });

    it('sorts days_asc with shorter-listed products first', () => {
        const sorted = sortTaskProducts([older, newer], 'days_asc', scoreFn, task);
        assert.equal(sorted[0], newer);
        assert.equal(sorted[1], older);
    });
});
