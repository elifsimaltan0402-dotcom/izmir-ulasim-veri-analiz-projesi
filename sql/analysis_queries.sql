-- ============================================================
-- ESHOT VERİ ANALİZİ SQL SORGULARI
-- ============================================================


-- name: total_stops
-- Toplam durak sayısı
SELECT
    COUNT(*) AS total_stops
FROM stops;


-- name: valid_coordinate_stops
-- Geçerli koordinata sahip durak sayısı
SELECT
    COUNT(*) AS valid_coordinate_stops
FROM stops
WHERE has_valid_coordinate = 1;


-- name: invalid_coordinate_stops
-- Koordinatı eksik veya geçersiz durak sayısı
SELECT
    COUNT(*) AS invalid_coordinate_stops
FROM stops
WHERE has_valid_coordinate = 0;


-- name: stops_without_routes
-- Hat bilgisi olmayan durak sayısı
SELECT
    COUNT(*) AS stops_without_routes
FROM stops AS s
LEFT JOIN stop_routes AS sr
    ON s.stop_id = sr.stop_id
WHERE sr.stop_id IS NULL;


-- name: total_unique_routes
-- Toplam benzersiz hat sayısı
SELECT
    COUNT(*) AS total_unique_routes
FROM routes;


-- name: total_stop_route_relations
-- Toplam durak-hat ilişkisi sayısı
SELECT
    COUNT(*) AS total_stop_route_relations
FROM stop_routes;


-- name: total_quality_issues
-- Toplam veri kalitesi sorunu sayısı
SELECT
    COUNT(*) AS total_quality_issues
FROM data_quality_issues;


-- name: top_10_routes
-- En fazla benzersiz duraktan geçen 10 hat
SELECT
    sr.route_number,
    COUNT(DISTINCT sr.stop_id) AS stop_count
FROM stop_routes AS sr
GROUP BY sr.route_number
ORDER BY
    stop_count DESC,
    CAST(sr.route_number AS INTEGER) ASC,
    sr.route_number ASC
LIMIT 10;


-- name: top_10_stops
-- En fazla farklı hattın geçtiği 10 durak
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
ORDER BY
    route_count DESC,
    s.stop_name ASC,
    s.stop_id ASC
LIMIT 10;


-- name: duplicate_stop_names
-- Aynı ada sahip birden fazla durak
SELECT
    stop_name,
    COUNT(DISTINCT stop_id) AS stop_count
FROM stops
GROUP BY stop_name
HAVING COUNT(DISTINCT stop_id) > 1
ORDER BY
    stop_count DESC,
    stop_name ASC;


-- name: route_stop_counts
-- Her hat için geçtiği benzersiz durak sayısı
SELECT
    r.route_number,
    COUNT(DISTINCT sr.stop_id) AS stop_count
FROM routes AS r
LEFT JOIN stop_routes AS sr
    ON r.route_number = sr.route_number
GROUP BY r.route_number
ORDER BY
    stop_count DESC,
    CAST(r.route_number AS INTEGER) ASC,
    r.route_number ASC;


-- name: single_route_stop_count
-- Sadece bir hattın geçtiği durakların sayısı
SELECT
    COUNT(*) AS single_route_stop_count
FROM (
    SELECT
        s.stop_id
    FROM stops AS s
    INNER JOIN stop_routes AS sr
        ON s.stop_id = sr.stop_id
    GROUP BY s.stop_id
    HAVING COUNT(DISTINCT sr.route_number) = 1
) AS single_route_stops;


-- name: stops_with_more_than_five_routes
-- Beşten fazla hattın geçtiği duraklar
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
HAVING COUNT(DISTINCT sr.route_number) > 5
ORDER BY
    route_count DESC,
    s.stop_name ASC,
    s.stop_id ASC;


-- name: data_quality_summary
-- Veri kalitesi sorunlarının türlerine göre dağılımı
SELECT
    issue_type,
    COUNT(*) AS issue_count
FROM data_quality_issues
GROUP BY issue_type
ORDER BY
    issue_count DESC,
    issue_type ASC;