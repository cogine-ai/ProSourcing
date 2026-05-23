import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
    buildReportPagination,
    getListedDays,
    sortTaskProducts,
    getTopCategoryZhLabel,
} from '../frontend_pro/src/components/reports/reportUtils.js';

const daysAgoIso = (days) => {
    const date = new Date();
    date.setUTCDate(date.getUTCDate() - days);
    return date.toISOString().replace(/\.\d{3}Z$/, 'Z');
};

const makeProduct = (createdDt, overrides = {}) => ({
    products_raw_data: {
        created_dt: createdDt,
        sale_qty: 1,
        review_qty: 1,
        sale_price: 100,
        ...overrides,
    },
});

describe('buildReportPagination', () => {
    it('returns empty array for invalid total page counts', () => {
        assert.deepEqual(buildReportPagination(1, 0), []);
        assert.deepEqual(buildReportPagination(1, -3), []);
        assert.deepEqual(buildReportPagination(1, Number.NaN), []);
    });

    it('clamps current page into valid range', () => {
        assert.deepEqual(
            buildReportPagination(99, 5),
            [1, 2, 3, 4, 5],
        );
        assert.deepEqual(
            buildReportPagination(-2, 3),
            [1, 2, 3],
        );
    });

    it('builds compact pagination for seven or fewer pages', () => {
        assert.deepEqual(buildReportPagination(2, 4), [1, 2, 3, 4]);
    });

    it('builds early, late, and middle window layouts', () => {
        assert.deepEqual(
            buildReportPagination(2, 12),
            [1, 2, 3, 4, 5, 'ellipsis-right', 12],
        );
        assert.deepEqual(
            buildReportPagination(10, 12),
            [1, 'ellipsis-left', 8, 9, 10, 11, 12],
        );
        assert.deepEqual(
            buildReportPagination(6, 12),
            [1, 'ellipsis-left', 5, 6, 7, 'ellipsis-right', 12],
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
        const listedDays = getListedDays(daysAgoIso(10));
        assert.ok(listedDays >= 10 && listedDays <= 11);
    });

    it('parses datetime strings with fractional seconds', () => {
        const listedDays = getListedDays(`${daysAgoIso(3).replace('Z', '')}.123456`);
        assert.ok(listedDays >= 3 && listedDays <= 4);
    });
});

describe('sortTaskProducts', () => {
    const getMetricScore = () => 0;

    it('sorts days_desc with older listings first', () => {
        const older = makeProduct(daysAgoIso(30));
        const newer = makeProduct(daysAgoIso(3));
        const sorted = sortTaskProducts([newer, older], 'days_desc', getMetricScore, null);

        assert.equal(sorted[0], older);
        assert.equal(sorted[1], newer);
    });

    it('sorts days_asc with newer listings first', () => {
        const older = makeProduct(daysAgoIso(30));
        const newer = makeProduct(daysAgoIso(3));
        const sorted = sortTaskProducts([older, newer], 'days_asc', getMetricScore, null);

        assert.equal(sorted[0], newer);
        assert.equal(sorted[1], older);
    });
});

describe('getTopCategoryZhLabel', () => {
    it('ignores malformed up_categories JSON instead of throwing', () => {
        const label = getTopCategoryZhLabel({
            up_categories: 'not-json',
        });
        assert.equal(label, '一级分类');
    });

    it('prefers explicit Chinese top category labels', () => {
        const label = getTopCategoryZhLabel({
            top_category_name_cn: '宠物用品',
            up_categories: [],
        });
        assert.equal(label, '宠物用品');
    });
});
