import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import {
    buildReportPagination,
    getListedDays,
    getCategoryDisplayName,
    buildCategoryNameLookup,
    sortTaskProducts,
} from './reportUtils.js';

describe('buildReportPagination', () => {
    it('returns empty array for invalid total pages', () => {
        assert.deepEqual(buildReportPagination(1, 0), []);
        assert.deepEqual(buildReportPagination(1, NaN), []);
        assert.deepEqual(buildReportPagination(1, -3), []);
    });

    it('returns all pages when total is seven or fewer', () => {
        assert.deepEqual(buildReportPagination(2, 5), [1, 2, 3, 4, 5]);
    });

    it('clamps current page into range', () => {
        assert.deepEqual(
            buildReportPagination(99, 10),
            [1, 'ellipsis-left', 6, 7, 8, 9, 10],
        );
        assert.deepEqual(
            buildReportPagination(0, 10),
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

    it('returns at least one day for a valid past timestamp', () => {
        const tenDaysAgo = new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString();
        assert.ok(getListedDays(tenDaysAgo) >= 9);
    });
});

describe('getCategoryDisplayName', () => {
    it('prefers Chinese names from the category tree lookup', () => {
        const lookup = buildCategoryNameLookup([
            { category_name: 'Телефоны', name_cn: '手机', children: [] },
        ]);
        const label = getCategoryDisplayName({ category_name: 'Телефоны' }, lookup);
        assert.equal(label, '手机');
    });
});

describe('sortTaskProducts', () => {
    const forceNum = (value) => Number(value) || 0;
    const getMetricScore = () => 0;

    it('sorts days_asc with fewer listed days first (newer listings)', () => {
        const older = {
            products_raw_data: {
                created_dt: new Date(Date.now() - 20 * 24 * 60 * 60 * 1000).toISOString(),
            },
        };
        const newer = {
            products_raw_data: {
                created_dt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
            },
        };
        const sorted = sortTaskProducts([older, newer], 'days_asc', getMetricScore, {}, forceNum);
        assert.equal(sorted[0], newer);
        assert.equal(sorted[1], older);
    });

    it('sorts days_desc with more listed days first (older listings)', () => {
        const older = {
            products_raw_data: {
                created_dt: new Date(Date.now() - 20 * 24 * 60 * 60 * 1000).toISOString(),
            },
        };
        const newer = {
            products_raw_data: {
                created_dt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
            },
        };
        const sorted = sortTaskProducts([newer, older], 'days_desc', getMetricScore, {}, forceNum);
        assert.equal(sorted[0], older);
        assert.equal(sorted[1], newer);
    });
});
