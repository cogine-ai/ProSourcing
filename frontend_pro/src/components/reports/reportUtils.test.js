import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import {
    buildReportPagination,
    getListedDays,
    getMetricScore,
    getTaskProductScore,
    isHighQualityProduct,
    sortTaskProducts,
} from './reportUtils.js';

const sampleAlgoConfig = {
    monthly_sales: { ranges: [1000, 500, 100], scores: [10, 8, 4, 0] },
    reviews: { ranges: [200, 50], scores: [3, 2, 0] },
    price: { ranges: [10000, 5000, 1000], scores: [2, 1, 0.5, 0] },
    days_per_review: { ranges: [1, 2, 2.5], scores: [3, 2, 1, 0] },
    avg_sales: { ranges: [20, 10], scores: [2, 1, 0] },
};

describe('buildReportPagination', () => {
    it('returns empty array for invalid totals', () => {
        assert.deepEqual(buildReportPagination(1, 0), []);
        assert.deepEqual(buildReportPagination(1, 'bad'), []);
    });

    it('clamps current page into valid range', () => {
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
        assert.deepEqual(
            buildReportPagination(10, 20),
            [1, 'ellipsis-left', 9, 10, 11, 'ellipsis-right', 20],
        );
    });
});

describe('getListedDays', () => {
    it('returns fallback for missing or invalid dates', () => {
        assert.equal(getListedDays(null), 999);
        assert.equal(getListedDays('not-a-date'), 999);
    });

    it('parses dotted timestamp strings', () => {
        const threeDaysAgo = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000);
        const formatted = threeDaysAgo.toISOString().replace('T', ' ').slice(0, 19);
        const days = getListedDays(`${formatted}.123`);
        assert.ok(days >= 2 && days <= 4);
    });
});

describe('getMetricScore', () => {
    it('returns zero without config', () => {
        assert.equal(getMetricScore('monthly_sales', 500, null, null), 0);
    });

    it('scores monthly sales by descending thresholds', () => {
        assert.equal(getMetricScore('monthly_sales', 1500, null, sampleAlgoConfig), 10);
        assert.equal(getMetricScore('monthly_sales', 120, null, sampleAlgoConfig), 4);
    });

    it('handles price tiers in reverse order', () => {
        assert.equal(getMetricScore('price', 12000, null, sampleAlgoConfig), 2);
        assert.equal(getMetricScore('price', 3000, null, sampleAlgoConfig), 0.5);
    });

    it('guards days_per_review when review count is zero', () => {
        assert.equal(getMetricScore('days_per_review', 30, 0, sampleAlgoConfig), 0);
        assert.equal(getMetricScore('days_per_review', 30, '--', sampleAlgoConfig), 0);
    });
});

describe('sortTaskProducts', () => {
    const older = {
        products_raw_data: {
            created_dt: '2020-01-01T00:00:00',
            sale_qty: 1,
            review_qty: 1,
            sale_price: 1,
        },
    };
    const newer = {
        products_raw_data: {
            created_dt: new Date().toISOString(),
            sale_qty: 1,
            review_qty: 1,
            sale_price: 1,
        },
    };
    const scoreFn = (metricKey, value, secondaryValue = null) =>
        getMetricScore(metricKey, value, secondaryValue, sampleAlgoConfig);

    it('sorts days_desc with older listings first', () => {
        const sorted = sortTaskProducts([older, newer], 'days_desc', scoreFn, {});
        assert.equal(sorted[0], older);
    });

    it('sorts days_asc with newer listings first', () => {
        const sorted = sortTaskProducts([older, newer], 'days_asc', scoreFn, {});
        assert.equal(sorted[0], newer);
    });
});

describe('isHighQualityProduct', () => {
    const forceNum = (value) => Number(value) || 0;

    it('rejects products outside filter thresholds', () => {
        const raw = {
            created_dt: new Date().toISOString(),
            sale_qty: 1,
            review_qty: 1,
            sale_price: 100,
        };
        const filters = { filterDays: 30, filterSales: 10, filterReviews: 5, filterMinPrice: 500 };
        assert.equal(isHighQualityProduct(raw, filters, forceNum), false);
    });
});

describe('getTaskProductScore', () => {
    it('aggregates metric scores for a product', () => {
        const scoreFn = (metricKey, value, secondaryValue = null) =>
            getMetricScore(metricKey, value, secondaryValue, sampleAlgoConfig);
        const task = { category_stats: { sale_qty: 100, sale_product_qty: 10 } };
        const score = getTaskProductScore(
            { products_raw_data: { sale_qty: 1500, review_qty: 250, sale_price: 12000, created_dt: new Date().toISOString() } },
            scoreFn,
            task,
        );
        assert.ok(score > 0);
    });
});
