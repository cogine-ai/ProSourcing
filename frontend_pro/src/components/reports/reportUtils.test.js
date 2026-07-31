import { describe, test } from 'node:test';
import assert from 'node:assert/strict';
import {
    anyCyrillic,
    buildCategoryNameLookup,
    buildReportPagination,
    getCategoryDisplayName,
    getListedDays,
    getTaskDurationLabel,
    getTopCategoryZhLabel,
    parsePreviewImage,
    sortTaskProducts,
} from './reportUtils.js';

const FIXED_NOW_MS = new Date('2026-06-07T12:00:00Z').getTime();

function withFixedNow(fn) {
    const realNow = Date.now;
    Date.now = () => FIXED_NOW_MS;
    try {
        fn();
    } finally {
        Date.now = realNow;
    }
}

describe('buildReportPagination', () => {
    test('returns empty array for non-positive totals', () => {
        assert.deepEqual(buildReportPagination(1, 0), []);
        assert.deepEqual(buildReportPagination(1, -3), []);
        assert.deepEqual(buildReportPagination(1, Number.NaN), []);
    });

    test('clamps invalid current page values', () => {
        assert.deepEqual(buildReportPagination(0, 5), [1, 2, 3, 4, 5]);
        assert.deepEqual(buildReportPagination(-2, 5), [1, 2, 3, 4, 5]);
        assert.deepEqual(buildReportPagination(99, 5), [1, 2, 3, 4, 5]);
        assert.deepEqual(buildReportPagination(2.9, 5), [1, 2, 3, 4, 5]);
    });

    test('builds ellipsis windows for large page counts', () => {
        assert.deepEqual(
            buildReportPagination(2, 10),
            [1, 2, 3, 4, 5, 'ellipsis-right', 10],
        );
        assert.deepEqual(
            buildReportPagination(8, 10),
            [1, 'ellipsis-left', 6, 7, 8, 9, 10],
        );
        assert.deepEqual(
            buildReportPagination(5, 10),
            [1, 'ellipsis-left', 4, 5, 6, 'ellipsis-right', 10],
        );
    });
});

describe('getListedDays', () => {
    test('returns fallback for missing or invalid values', () => {
        assert.equal(getListedDays(null), 999);
        assert.equal(getListedDays(undefined), 999);
        assert.equal(getListedDays(''), 999);
        assert.equal(getListedDays('not-a-date'), 999);
    });

    test('parses dotted datetime strings and enforces a minimum of one day', () => {
        withFixedNow(() => {
            assert.equal(getListedDays('2026-06-05 12:00:00.000'), 2);
            assert.equal(getListedDays('2026-06-07 12:00:00.000'), 1);
        });
    });
});

describe('sortTaskProducts listed-day ordering', () => {
    const noScore = () => 0;
    const task = {};
    const older = { products_raw_data: { created_dt: '2026-01-01T00:00:00' } };
    const newer = { products_raw_data: { created_dt: '2026-06-01T00:00:00' } };

    test('days_desc puts longer-listed products first', () => {
        withFixedNow(() => {
            const sorted = sortTaskProducts([newer, older], 'days_desc', noScore, task);
            assert.equal(sorted[0], older);
            assert.equal(sorted[1], newer);
        });
    });

    test('days_asc puts shorter-listed products first', () => {
        withFixedNow(() => {
            const sorted = sortTaskProducts([older, newer], 'days_asc', noScore, task);
            assert.equal(sorted[0], newer);
            assert.equal(sorted[1], older);
        });
    });
});

describe('category display helpers', () => {
    test('detects cyrillic text', () => {
        assert.equal(anyCyrillic('Телефоны'), true);
        assert.equal(anyCyrillic('手机'), false);
    });

    test('prefers Chinese labels from the category tree lookup', () => {
        const lookup = buildCategoryNameLookup([
            { name_ru: 'Телефоны', name_cn: '手机', children: [] },
        ]);
        assert.equal(
            getCategoryDisplayName({ category_name: 'Телефоны' }, lookup),
            '手机',
        );
    });

    test('parses stringified up_categories when resolving top labels', () => {
        const task = {
            up_categories: JSON.stringify([{ category_name: '手机', name_cn: '手机' }]),
        };
        assert.equal(getTopCategoryZhLabel(task), '手机');
    });
});

describe('misc report helpers', () => {
    test('formats valid task durations and guards invalid ranges', () => {
        assert.equal(
            getTaskDurationLabel({
                created_at: '2026-06-07T10:00:00',
                finished_at: '2026-06-07T10:02:05',
            }),
            '2m 5s',
        );
        assert.equal(
            getTaskDurationLabel({
                created_at: '2026-06-07T10:00:00',
                finished_at: '2026-06-07T09:00:00',
            }),
            '--',
        );
    });

    test('parses preview image payloads safely', () => {
        assert.equal(parsePreviewImage('not-json'), '');
        assert.equal(
            parsePreviewImage(JSON.stringify([{ medium: 'https://img.example/a.jpg' }])),
            'https://img.example/a.jpg',
        );
    });
});
