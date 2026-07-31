-- ============================================================
-- ESHOT GELİŞMİŞ SQL GÖRÜNÜMLERİ VE SORGULARI
-- ============================================================

-- Bu dosyada:
-- CTE
-- Self join
-- GROUP BY
-- HAVING
-- Window function
-- yapıları kullanılmaktadır.


-- ============================================================
-- 1. HER DURAĞIN GEÇTİĞİ HAT SAYISI
-- ============================================================

DROP VIEW IF EXISTS vw_stop_route_counts;

CREATE VIEW vw_stop_route_counts AS
SELECT
    s.stop_id,
    s.stop_name,
    COUNT(DISTINCT sr.route_number) AS route_count
FROM stops AS s
LEFT JOIN stop_routes AS sr
    ON s.stop_id = sr.stop_id
GROUP BY
    s.stop_id,
    s.stop_name;


-- ============================================================
-- 2. HER HATTIN DURAK SAYISI
-- ============================================================

DROP VIEW IF EXISTS vw_route_stop_counts;

CREATE VIEW vw_route_stop_counts AS
SELECT
    r.route_number,
    COUNT(DISTINCT sr.stop_id) AS stop_count
FROM routes AS r
LEFT JOIN stop_routes AS sr
    ON r.route_number = sr.route_number
GROUP BY
    r.route_number;


-- ============================================================
-- 3. İKİ VEYA DAHA FAZLA HATTIN GEÇTİĞİ AKTARMA DURAKLARI
-- ============================================================

DROP VIEW IF EXISTS vw_transfer_stops;

CREATE VIEW vw_transfer_stops AS
SELECT
    s.stop_id,
    s.stop_name,
    COUNT(DISTINCT sr.route_number) AS route_count
FROM stops AS s
INNER JOIN stop_routes AS sr
    ON s.stop_id = sr.stop_id
GROUP BY
    s.stop_id,
    s.stop_name
HAVING COUNT(DISTINCT sr.route_number) >= 2;


-- ============================================================
-- 4. EN FAZLA AKTARMA SEÇENEĞİ SUNAN DURAKLAR
-- Window function kullanılmıştır.
-- ============================================================

DROP VIEW IF EXISTS vw_top_transfer_stops;

CREATE VIEW vw_top_transfer_stops AS
WITH transfer_counts AS (
    SELECT
        s.stop_id,
        s.stop_name,
        COUNT(DISTINCT sr.route_number) AS route_count
    FROM stops AS s
    INNER JOIN stop_routes AS sr
        ON s.stop_id = sr.stop_id
    GROUP BY
        s.stop_id,
        s.stop_name
),
ranked_transfer_stops AS (
    SELECT
        stop_id,
        stop_name,
        route_count,
        DENSE_RANK() OVER (
            ORDER BY route_count DESC
        ) AS transfer_rank
    FROM transfer_counts
)
SELECT
    stop_id,
    stop_name,
    route_count,
    transfer_rank
FROM ranked_transfer_stops;


-- ============================================================
-- 5. AYNI DURAĞI KULLANAN HAT ÇİFTLERİ
-- Self join kullanılmıştır.
--
-- sr1.route_number < sr2.route_number koşulu sayesinde:
-- 121-140 oluşturulur,
-- 140-121 tekrar oluşturulmaz.
-- ============================================================

DROP VIEW IF EXISTS vw_route_pairs_by_stop;

CREATE VIEW vw_route_pairs_by_stop AS
SELECT
    sr1.stop_id,
    s.stop_name,
    sr1.route_number AS route_1,
    sr2.route_number AS route_2
FROM stop_routes AS sr1
INNER JOIN stop_routes AS sr2
    ON sr1.stop_id = sr2.stop_id
    AND sr1.route_number < sr2.route_number
INNER JOIN stops AS s
    ON sr1.stop_id = s.stop_id;


-- ============================================================
-- 6. HER HAT ÇİFTİ İÇİN ORTAK DURAK SAYISI
-- ============================================================

DROP VIEW IF EXISTS vw_route_pair_common_stop_counts;

CREATE VIEW vw_route_pair_common_stop_counts AS
WITH route_pairs AS (
    SELECT
        sr1.route_number AS route_1,
        sr2.route_number AS route_2,
        sr1.stop_id
    FROM stop_routes AS sr1
    INNER JOIN stop_routes AS sr2
        ON sr1.stop_id = sr2.stop_id
        AND sr1.route_number < sr2.route_number
)
SELECT
    route_1,
    route_2,
    COUNT(DISTINCT stop_id) AS common_stop_count
FROM route_pairs
GROUP BY
    route_1,
    route_2;


-- ============================================================
-- 7. EN FAZLA ORTAK DURAĞA SAHİP HAT ÇİFTLERİ
-- Window function kullanılmıştır.
-- ============================================================

DROP VIEW IF EXISTS vw_top_route_pairs;

CREATE VIEW vw_top_route_pairs AS
WITH route_pair_counts AS (
    SELECT
        sr1.route_number AS route_1,
        sr2.route_number AS route_2,
        COUNT(DISTINCT sr1.stop_id) AS common_stop_count
    FROM stop_routes AS sr1
    INNER JOIN stop_routes AS sr2
        ON sr1.stop_id = sr2.stop_id
        AND sr1.route_number < sr2.route_number
    GROUP BY
        sr1.route_number,
        sr2.route_number
),
ranked_route_pairs AS (
    SELECT
        route_1,
        route_2,
        common_stop_count,
        DENSE_RANK() OVER (
            ORDER BY common_stop_count DESC
        ) AS common_stop_rank
    FROM route_pair_counts
)
SELECT
    route_1,
    route_2,
    common_stop_count,
    common_stop_rank
FROM ranked_route_pairs;


-- ============================================================
-- 8. HATTI OLMAYAN DURAKLAR
-- ============================================================

DROP VIEW IF EXISTS vw_stops_without_routes;

CREATE VIEW vw_stops_without_routes AS
SELECT
    s.stop_id,
    s.stop_name,
    s.latitude,
    s.longitude
FROM stops AS s
LEFT JOIN stop_routes AS sr
    ON s.stop_id = sr.stop_id
WHERE sr.stop_id IS NULL;


-- ============================================================
-- 9. GEÇERSİZ KOORDİNATLI DURAKLAR
-- ============================================================

DROP VIEW IF EXISTS vw_invalid_coordinate_stops;

CREATE VIEW vw_invalid_coordinate_stops AS
SELECT
    stop_id,
    stop_name,
    latitude,
    longitude,
    has_valid_coordinate
FROM stops
WHERE has_valid_coordinate = 0;


-- ============================================================
-- 10. AYNI İSİMLİ FAKAT FARKLI ID'YE SAHİP DURAKLAR
-- GROUP BY ve HAVING kullanılmıştır.
-- ============================================================

DROP VIEW IF EXISTS vw_duplicate_stop_names;

CREATE VIEW vw_duplicate_stop_names AS
WITH duplicate_names AS (
    SELECT
        stop_name
    FROM stops
    GROUP BY
        stop_name
    HAVING COUNT(DISTINCT stop_id) > 1
)
SELECT
    s.stop_id,
    s.stop_name,
    s.latitude,
    s.longitude
FROM stops AS s
INNER JOIN duplicate_names AS d
    ON s.stop_name = d.stop_name;