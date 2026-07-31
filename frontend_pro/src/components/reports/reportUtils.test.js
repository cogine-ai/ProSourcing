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
    });

    it('reads medium url from json string list', () => {
        const payload = JSON.stringify([{ medium: 'https://example.com/m.jpg' }]);
        assert.equal(parsePreviewImage(payload, 'medium'), 'https://example.com/m.jpg');
    });
});

describe('getCategoryDisplayName', () => {
    const lookup = buildCategoryNameLookup([
        {
            name_cn: '手机配件',
            name_ru: 'Аксессуары для телефонов',
            children: [],
        },
    ]);

    it('prefers non-cyrillic Chinese name on the category object', () => {
        const cat = { name_cn: '蓝牙耳机', name_ru: 'Наушники' };
        assert.equal(getCategoryDisplayName(cat, lookup), '蓝牙耳机');
    });

    it('resolves Russian name via category tree lookup', () => {
        const cat = { name_ru: 'Аксессуары для телефонов' };
        assert.equal(getCategoryDisplayName(cat, lookup), '手机配件');
    });

    it('extracts Chinese from RPA采集_ prefix when lookup misses', () => {
        const cat = { category_name: 'RPA采集_厨房用品(厨具)' };
        assert.equal(getCategoryDisplayName(cat, new Map()), '厨具');
    });

    it('returns 未知品类 for empty input', () => {
        assert.equal(getCategoryDisplayName(null, lookup), '未知品类');
    });
});

describe('getTopCategoryZhLabel', () => {
    const lookup = buildCategoryNameLookup([
        { name_cn: '大家电', name_ru: 'Крупная бытовая техника', children: [] },
    ]);

    it('uses task.top_category_name_cn when present', () => {
        const task = { top_category_name_cn: '美妆个护' };
        assert.equal(getTopCategoryZhLabel(task, [], lookup), '美妆个护');
    });

    it('parses up_categories json string and resolves Chinese label', () => {
        const task = {
            up_categories: JSON.stringify([{ name_ru: 'Крупная бытовая техника' }]),
        };
        assert.equal(getTopCategoryZhLabel(task, [], lookup), '大家电');
    });

    it('falls back to 一级分类 when path is empty', () => {
        assert.equal(getTopCategoryZhLabel({}, [], lookup), '一级分类');
    });
});
