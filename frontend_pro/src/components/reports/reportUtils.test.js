import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import {
    buildCategoryNameLookup,
    buildReportPagination,
    getCategoryDisplayName,
    getListedDays,
    getTopCategoryZhLabel,
    parsePreviewImage,
    sortTaskProducts,
} from './reportUtils.js';

describe('buildReportPagination', () => {
    it('returns empty array for invalid total pages', () => {
        assert.deepEqual(buildReportPagination(1, 0), []);
        assert.deepEqual(buildReportPagination(1, -3), []);
        assert.deepEqual(buildReportPagination(1, Number.NaN), []);
    });

    it('returns all pages when total is seven or fewer', () => {
        assert.deepEqual(buildReportPagination(2, 5), [1, 2, 3, 4, 5]);
    });

    it('clamps invalid current page into range', () => {
        assert.deepEqual(buildReportPagination(0, 5), [1, 2, 3, 4, 5]);
        assert.deepEqual(buildReportPagination(99, 5), [1, 2, 3, 4, 5]);
        assert.deepEqual(buildReportPagination(Number.NaN, 3), [1, 2, 3]);
        assert.deepEqual(
            buildReportPagination(99, 10),
            [1, 'ellipsis-left', 6, 7, 8, 9, 10],
        );
    });

    it('builds ellipsis windows for large page counts', () => {
        assert.deepEqual(
            buildReportPagination(3, 20),
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
        assert.equal(getListedDays(''), 999);
        assert.equal(getListedDays('not-a-real-date'), 999);
    });

    it('parses dotted datetime strings', () => {
        const days = getListedDays('2020-01-15 10:20:30.123');
        assert.ok(Number.isFinite(days));
        assert.ok(days > 100);
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

describe('sortTaskProducts listed-day ordering', () => {
    const noopScore = () => 0;
    const older = { products_raw_data: { created_dt: '2018-01-01T00:00:00' } };
    const newer = { products_raw_data: { created_dt: '2024-06-01T00:00:00' } };

    it('sorts days_desc with older listings first', () => {
        const sorted = sortTaskProducts([newer, older], 'days_desc', noopScore, {});
        assert.equal(sorted[0], older);
        assert.equal(sorted[1], newer);
    });

    it('sorts days_asc with newer listings first', () => {
        const sorted = sortTaskProducts([older, newer], 'days_asc', noopScore, {});
        assert.equal(sorted[0], newer);
        assert.equal(sorted[1], older);
    });
});

describe('getTopCategoryZhLabel JSON parsing', () => {
    it('parses up_categories JSON string safely', () => {
        const task = {
            up_categories: JSON.stringify([{ name_cn: '宠物用品' }]),
        };
        assert.equal(getTopCategoryZhLabel(task), '宠物用品');
    });

    it('returns default label when up_categories JSON is invalid', () => {
        const task = { up_categories: 'not-json' };
        assert.equal(getTopCategoryZhLabel(task), '一级分类');
    });
});

describe('parsePreviewImage', () => {
    it('returns empty string for malformed JSON without throwing', () => {
        assert.equal(parsePreviewImage('not-json'), '');
    });

    it('reads preview URL from JSON array payload', () => {
        const payload = JSON.stringify([{ medium: 'https://example.com/img.jpg' }]);
        assert.equal(parsePreviewImage(payload), 'https://example.com/img.jpg');
    });
});
