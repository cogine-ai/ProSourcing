import os

import psycopg2


VERIFIED_TOP_CATEGORY_COUNTS = {
    "00933": 1939806,
    "00299": 493504,
    "00751": 772686,
    "00240": 1565665,
    "06498": 1058193,
    "00083": 333258,
    "00002": 1484102,
    "02807": 100437,
    "00079": 1377666,
    "02605": 247301,
    "00791": 522075,
    "00147": 437012,
    "00239": 547487,
    "00754": 533712,
    "00005": 365904,
    "00864": 395022,
    "02062": 126858,
    "00034": 101593,
    "01793": 23144,
    "00012": 62256,
    "01466": 85313,
}


def main():
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:prosourcing123@db:5432/prosourcing",
    )

    with psycopg2.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                UPDATE categories
                SET sale_product_qty = %s
                WHERE category_id = %s
                   OR (is_top_level = TRUE AND algatop_id = %s)
                """,
                [(value, category_id, category_id) for category_id, value in VERIFIED_TOP_CATEGORY_COUNTS.items()],
            )
        conn.commit()

    print(f"[DONE] Applied verified top category counts: {len(VERIFIED_TOP_CATEGORY_COUNTS)}")


if __name__ == "__main__":
    main()
