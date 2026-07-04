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
    it('returns empty array for invalid total pages', () => {
        assert.deepEqual(buildReportPagination(1, 0), []);
        assert.deepEqual(buildReportPagination(1, NaN), []);
        assert.deepEqual(buildReportPagination(1, -3), []);
    });

    it('clamps current page into range', () => {
        assert.deepEqual(buildReportPagination(99, 3), [1, 2, 3]);
        assert.deepEqual(buildReportPagination(-5, 3), [1, 2, 3]);
    });

    it('builds ellipsis windows for large page counts', () => {
        assert.deepEqual(buildReportPagination(2, 10), [1, 2, 3, 4, 5, 'ellipsis-right', 10]);
        assert.deepEqual(
            buildReportPagination(9, 10),
            [1, 'ellipsis-left', 6, 7, 8, 9, 10],
        );
        assert.deepEqual(
            buildReportPagination(5, 10),
            [1, 'ellipsis-left', 4, 5, 6, 'ellipsis-right', 10],
        );
    });
});

describe('getListedDays', () => {
    it('returns fallback for missing or invalid dates', () => {
        assert.equal(getListedDays(null), 999);
        assert.equal(getListedDays(''), 999);
        assert.equal(getListedDays('not-a-date'), 999);
    });

    it('returns at least 1 day for a valid past timestamp', () => {
        const threeDaysAgo = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString();
        assert.equal(getListedDays(threeDaysAgo), 3);
    });
});

describe('sortTaskProducts days_asc / days_desc', () => {
    const older = {
        products_raw_data: { created_dt: '2020-01-01T00:00:00' },
    };
    const newer = {
        products_raw_data: { created_dt: '2024-06-01T00:00:00' },
    };
    const noopScore = () => 0;

    it('days_desc sorts by listed-days descending (longer on shelf first)', () => {
        const sorted = sortTaskProducts([older, newer], 'days_desc', noopScore, {});
        assert.equal(sorted[0], older);
        assert.equal(sorted[1], newer);
    });

    it('days_asc sorts by listed-days ascending (newer listings first)', () => {
        const sorted = sortTaskProducts([older, newer], 'days_asc', noopScore, {});
        assert.equal(sorted[0], newer);
        assert.equal(sorted[1], older);
    });
});

describe('parsePreviewImage', () => {
    it('returns empty string for invalid json without throwing', () => {
        assert.equal(parsePreviewImage('not-json'), '');
        assert.equal(parsePreviewImage('12345'), '');
        assert.equal(parsePreviewImage(''), '');
    });

    it('reads medium url from json string list', () => {
        const payload = JSON.stringify([{ medium: 'https://example.com/m.jpg' }]);
        assert.equal(parsePreviewImage(payload, 'medium'), 'https://example.com/m.jpg');
    });
});

describe('getTopCategoryZhLabel', () => {
    it('returns top_category_name_cn when present', () => {
        assert.equal(
            getTopCategoryZhLabel({ top_category_name_cn: '电子产品' }),
            '电子产品',
        );
    });

    it('handles malformed up_categories json without throwing', () => {
        assert.equal(
            getTopCategoryZhLabel({ up_categories: 'not-json' }),
            '一级分类',
        );
        assert.equal(
            getTopCategoryZhLabel({ up_categories: '{broken' }),
            '一级分类',
        );
    });

    it('resolves zh label from parsed up_categories array', () => {
        const task = {
            up_categories: JSON.stringify([
                { category_name_cn: '家居用品', category_name: 'Home' },
            ]),
        };
        assert.equal(getTopCategoryZhLabel(task), '家居用品');
    });
});
