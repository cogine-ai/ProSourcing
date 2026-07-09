import assert from 'node:assert/strict';
import { after, describe, it } from 'node:test';
import {
    anyCyrillic,
    buildCategoryNameLookup,
    buildReportPagination,
    filterTaskProducts,
    getAverageSalesPerProduct,
    getCategoryDisplayName,
    getListedDays,
    getTaskDurationLabel,
    getTopCategoryZhLabel,
    isHighQualityProduct,
    parsePreviewImage,
    sortTaskProducts,
} from './reportUtils.js';

const forceNum = (value) => {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : 0;
};

const scoreStub = () => 0;

describe('buildReportPagination', () => {
    it('returns empty array for invalid totals', () => {
        assert.deepEqual(buildReportPagination(1, 0), []);
        assert.deepEqual(buildReportPagination(1, -3), []);
        assert.deepEqual(buildReportPagination(1, Number.NaN), []);
    });

    it('returns all page numbers when total pages is small', () => {
        assert.deepEqual(buildReportPagination(2, 5), [1, 2, 3, 4, 5]);
    });

    it('clamps current page to the last page for trailing windows', () => {
        assert.deepEqual(
            buildReportPagination(99, 10),
            [1, 'ellipsis-left', 6, 7, 8, 9, 10],
        );
    });

    it('shows a middle ellipsis window for interior pages', () => {
        assert.deepEqual(
            buildReportPagination(5, 10),
            [1, 'ellipsis-left', 4, 5, 6, 'ellipsis-right', 10],
        );
    });
});

describe('getListedDays', () => {
    const realDateNow = Date.now;

    after(() => {
        Date.now = realDateNow;
    });

    it('returns fallback for missing or invalid dates', () => {
        assert.equal(getListedDays(null), 999);
        assert.equal(getListedDays('not-a-date'), 999);
    });

    it('parses dotted datetime strings and counts whole days', () => {
        const fixedNow = new Date('2026-05-30T12:00:00Z').getTime();
        Date.now = () => fixedNow;

        assert.equal(getListedDays('2026-05-20 10:00:00.000'), 10);
    });
});

describe('sortTaskProducts listed-day ordering', () => {
    const realDateNow = Date.now;

    after(() => {
        Date.now = realDateNow;
    });

    const older = { products_raw_data: { created_dt: '2026-01-01T00:00:00' } };
    const newer = { products_raw_data: { created_dt: '2026-05-01T00:00:00' } };

    it('sorts days_desc with older listings first', () => {
        Date.now = () => new Date('2026-05-30T00:00:00Z').getTime();

        const sorted = sortTaskProducts([newer, older], 'days_desc', scoreStub, null);
        assert.equal(sorted[0], older);
        assert.equal(sorted[1], newer);
    });

    it('sorts days_asc with newer listings first', () => {
        Date.now = () => new Date('2026-05-30T00:00:00Z').getTime();

        const sorted = sortTaskProducts([older, newer], 'days_asc', scoreStub, null);
        assert.equal(sorted[0], newer);
        assert.equal(sorted[1], older);
    });
});

describe('getTaskDurationLabel', () => {
    it('prefers explicit duration and guards invalid ranges', () => {
        assert.equal(getTaskDurationLabel({ duration: '3m 4s' }), '3m 4s');
        assert.equal(
            getTaskDurationLabel({
                created_at: '2026-05-30T10:00:00',
                finished_at: '2026-05-30T09:00:00',
            }),
            '--',
        );
        assert.equal(
            getTaskDurationLabel({
                created_at: '2026-05-30T10:00:00',
                finished_at: '2026-05-30T10:02:05',
            }),
            '2m 5s',
        );
    });
});

describe('category display helpers', () => {
    it('detects cyrillic text', () => {
        assert.equal(anyCyrillic('Телефоны'), true);
        assert.equal(anyCyrillic('手机'), false);
    });

    it('builds lookup keys from nested category nodes', () => {
        const lookup = buildCategoryNameLookup([
            {
                name_cn: '手机',
                name_ru: 'Телефоны',
                children: [{ name_cn: '配件', category_name: 'Accessories (配件)' }],
            },
        ]);

        assert.equal(lookup.get('телефоны'), '手机');
        assert.equal(lookup.get('accessories'), '配件');
    });

    it('resolves Chinese labels from parentheses and tree lookup', () => {
        assert.equal(getCategoryDisplayName({ category_name: 'Phones (手机)' }), '手机');

        const lookup = buildCategoryNameLookup([{ name_cn: '无人机', name_ru: 'Drones' }]);
        assert.equal(getCategoryDisplayName({ name_ru: 'Drones' }, lookup), '无人机');
    });

    it('parses up_categories JSON strings for top labels', () => {
        const task = {
            up_categories: JSON.stringify([{ category_name: 'Phones (手机)' }]),
        };
        assert.equal(getTopCategoryZhLabel(task), '手机');
    });
});

describe('product filtering helpers', () => {
    const realDateNow = Date.now;

    after(() => {
        Date.now = realDateNow;
    });

    it('filters high-quality products using numeric thresholds', () => {
        Date.now = () => new Date('2026-05-30T00:00:00Z').getTime();

        const raw = {
            created_dt: '2026-05-20T00:00:00',
            sale_qty: 120,
            review_qty: 40,
            sale_price: 9000,
        };

        assert.equal(
            isHighQualityProduct(
                raw,
                { filterDays: 30, filterSales: 100, filterReviews: 20, filterMinPrice: 5000 },
                forceNum,
            ),
            true,
        );
        assert.equal(
            isHighQualityProduct(
                raw,
                { filterDays: 5, filterSales: 100, filterReviews: 20, filterMinPrice: 5000 },
                forceNum,
            ),
            false,
        );
    });

    it('parses preview image JSON safely', () => {
        const payload = JSON.stringify([
            { medium: 'https://example.com/m.jpg', large: 'https://example.com/l.jpg' },
        ]);
        assert.equal(parsePreviewImage(payload, 'large'), 'https://example.com/l.jpg');
        assert.equal(parsePreviewImage('not-json'), '');
    });
});

describe('filterTaskProducts and average sales', () => {
    const realDateNow = Date.now;

    after(() => {
        Date.now = realDateNow;
    });

    it('returns all products when onlyHighQuality is false', () => {
        const products = [
            { products_raw_data: { sale_qty: 0 } },
            { products_raw_data: { sale_qty: 10 } },
        ];
        assert.equal(filterTaskProducts(products, false, {}, forceNum).length, 2);
    });

    it('filters to high-quality products only', () => {
        Date.now = () => new Date('2026-05-30T00:00:00Z').getTime();

        const products = [
            {
                products_raw_data: {
                    created_dt: '2026-05-20T00:00:00',
                    sale_qty: 5,
                    review_qty: 1,
                    sale_price: 100,
                },
            },
            {
                products_raw_data: {
                    created_dt: '2026-05-20T00:00:00',
                    sale_qty: 120,
                    review_qty: 40,
                    sale_price: 9000,
                },
            },
        ];

        const filters = {
            filterDays: 30,
            filterSales: 100,
            filterReviews: 20,
            filterMinPrice: 5000,
        };

        const filtered = filterTaskProducts(products, true, filters, forceNum);
        assert.equal(filtered.length, 1);
        assert.equal(filtered[0].products_raw_data.sale_qty, 120);
    });

    it('computes average sales per product with safe fallbacks', () => {
        assert.equal(getAverageSalesPerProduct({ category_stats: { sale_qty: 100, sale_product_qty: 4 } }), 25);
        assert.equal(getAverageSalesPerProduct({ category_stats: { sale_qty: 10, sale_product_qty: 0 } }), 0);
        assert.equal(getAverageSalesPerProduct(null), 0);
    });
});
