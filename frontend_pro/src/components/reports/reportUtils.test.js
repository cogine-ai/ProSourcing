import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import {
    buildReportPagination,
    getListedDays,
    sortTaskProducts,
} from './reportUtils.js';

describe('getListedDays', () => {
    it('returns fallback for missing or invalid dates', () => {
        assert.equal(getListedDays(null), 999);
        assert.equal(getListedDays(''), 999);
        assert.equal(getListedDays('not-a-date'), 999);
    });

    it('parses dotted datetime strings', () => {
        const days = getListedDays('2020-01-01 00:00:00.000');
        assert.ok(Number.isFinite(days));
        assert.ok(days >= 1);
    });
});

describe('buildReportPagination', () => {
    it('returns empty array for non-positive totals', () => {
        assert.deepEqual(buildReportPagination(1, 0), []);
        assert.deepEqual(buildReportPagination(1, -3), []);
        assert.deepEqual(buildReportPagination(1, Number.NaN), []);
    });

    it('clamps invalid current page values', () => {
        assert.deepEqual(
            buildReportPagination(-5, 3),
            [1, 2, 3],
        );
        assert.deepEqual(
            buildReportPagination(99, 3),
            [1, 2, 3],
        );
    });

    it('builds ellipsis windows for large page counts', () => {
        assert.deepEqual(
            buildReportPagination(2, 20),
            [1, 2, 3, 4, 5, 'ellipsis-right', 20],
        );
        assert.deepEqual(
            buildReportPagination(18, 20),
            [1, 'ellipsis-left', 16, 17, 18, 19, 20],
        );
    });
});

describe('sortTaskProducts listed-day ordering', () => {
    const scoreFn = () => 0;
    const selectedTask = {};

    const older = {
        products_raw_data: { created_dt: '2018-06-01 00:00:00' },
    };
    const newer = {
        products_raw_data: { created_dt: '2024-06-01 00:00:00' },
    };

    it('sorts days_asc with fewer listed days first', () => {
        const sorted = sortTaskProducts([older, newer], 'days_asc', scoreFn, selectedTask);
        assert.equal(sorted[0], newer);
        assert.equal(sorted[1], older);
    });

    it('sorts days_desc with more listed days first', () => {
        const sorted = sortTaskProducts([newer, older], 'days_desc', scoreFn, selectedTask);
        assert.equal(sorted[0], older);
        assert.equal(sorted[1], newer);
    });
});
