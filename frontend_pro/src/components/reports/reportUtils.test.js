import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

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

describe('getCategoryDisplayName', () => {
    it('prefers non-cyrillic Chinese names', () => {
        const cat = { name_cn: '手机配件', category_name: 'Аксессуары (手机配件)' };
        assert.equal(getCategoryDisplayName(cat), '手机配件');
    });

    it('extracts Chinese text from parenthetical category names', () => {
        const cat = { category_name: 'Бытовая техника (家用电器)' };
        assert.equal(getCategoryDisplayName(cat), '家用电器');
    });

    it('resolves names from category tree lookup', () => {
        const lookup = buildCategoryNameLookup([
            { name_ru: 'Elektronika', name_cn: '电子产品', children: [] },
        ]);
        assert.equal(getCategoryDisplayName({ name_ru: 'Elektronika' }, lookup), '电子产品');
    });
});

describe('getTopCategoryZhLabel', () => {
    it('parses JSON string up_categories safely', () => {
        const task = {
            up_categories: '[{"category_name":"Бытовая техника (家用电器)"}]',
        };
        assert.equal(getTopCategoryZhLabel(task), '家用电器');
    });

    it('ignores malformed JSON in up_categories', () => {
        const task = { up_categories: 'not-json' };
        assert.equal(getTopCategoryZhLabel(task), '一级分类');
    });
});

describe('parsePreviewImage', () => {
    it('returns empty string for invalid JSON payloads', () => {
        assert.equal(parsePreviewImage('not-json'), '');
    });

    it('returns requested image size when present', () => {
        const payload = JSON.stringify([{ medium: 'm.jpg', large: 'l.jpg' }]);
        assert.equal(parsePreviewImage(payload, 'large'), 'l.jpg');
    });
});
