import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import {
    buildReportPagination,
    getListedDays,
    getTopCategoryZhLabel,
    parsePreviewImage,
    sortTaskProducts,
} from './reportUtils.js';

describe('buildReportPagination', () => {
    it('returns empty array for non-positive total pages', () => {
        assert.deepEqual(buildReportPagination(1, 0), []);
        assert.deepEqual(buildReportPagination(1, -3), []);
        assert.deepEqual(buildReportPagination(1, NaN), []);
    });

    it('clamps current page into valid range', () => {
        assert.deepEqual(buildReportPagination(0, 5), [1, 2, 3, 4, 5]);
        assert.deepEqual(buildReportPagination(99, 5), [1, 2, 3, 4, 5]);
        assert.deepEqual(buildReportPagination('2', '4'), [1, 2, 3, 4]);
    });

    it('builds ellipsis windows for large page counts', () => {
        assert.deepEqual(buildReportPagination(2, 10), [1, 2, 3, 4, 5, 'ellipsis-right', 10]);
        assert.deepEqual(buildReportPagination(8, 10), [1, 'ellipsis-left', 6, 7, 8, 9, 10]);
        assert.deepEqual(buildReportPagination(5, 10), [1, 'ellipsis-left', 4, 5, 6, 'ellipsis-right', 10]);
    });
});

describe('getListedDays', () => {
    it('returns fallback for missing or invalid dates', () => {
        assert.equal(getListedDays(null), 999);
        assert.equal(getListedDays(''), 999);
        assert.equal(getListedDays('not-a-date'), 999);
    });

    it('computes days from ISO-like strings', () => {
        const tenDaysAgo = new Date(Date.now() - 10 * 24 * 60 * 60 * 1000);
        const iso = tenDaysAgo.toISOString().replace('T', ' ').split('.')[0];
        assert.equal(getListedDays(iso), 10);
    });
});

describe('sortTaskProducts day sorting', () => {
    const getMetricScore = () => 0;
    const selectedTask = {};

    const older = { products_raw_data: { created_dt: '2020-01-01 00:00:00' } };
    const newer = { products_raw_data: { created_dt: '2024-06-01 00:00:00' } };

    it('days_asc puts newer listings first (fewer listed days)', () => {
        const sorted = sortTaskProducts([older, newer], 'days_asc', getMetricScore, selectedTask);
        assert.equal(sorted[0], newer);
        assert.equal(sorted[1], older);
    });

    it('days_desc puts older listings first (more listed days)', () => {
        const sorted = sortTaskProducts([newer, older], 'days_desc', getMetricScore, selectedTask);
        assert.equal(sorted[0], older);
        assert.equal(sorted[1], newer);
    });
});

describe('safe JSON parsing via public helpers', () => {
    it('getTopCategoryZhLabel tolerates malformed up_categories JSON', () => {
        const task = { up_categories: 'not-json', top_category_name_cn: null };
        assert.equal(getTopCategoryZhLabel(task, [], new Map()), '一级分类');
    });

    it('parsePreviewImage tolerates malformed preview JSON', () => {
        assert.equal(parsePreviewImage('garbage'), '');
        assert.equal(parsePreviewImage('{"medium":"https://img.test/a.jpg"}'), 'https://img.test/a.jpg');
    });
});
