PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS data_quality_issues;
DROP TABLE IF EXISTS stop_routes;
DROP TABLE IF EXISTS routes;
DROP TABLE IF EXISTS stops;

CREATE TABLE stops (
    stop_id INTEGER PRIMARY KEY,
    stop_name TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    has_valid_coordinate INTEGER NOT NULL
        CHECK (has_valid_coordinate IN (0, 1))
);

CREATE TABLE routes (
    route_number TEXT PRIMARY KEY
);

CREATE TABLE stop_routes (
    stop_id INTEGER NOT NULL,
    route_number TEXT NOT NULL,

    PRIMARY KEY (stop_id, route_number),

    FOREIGN KEY (stop_id)
        REFERENCES stops(stop_id)
        ON DELETE CASCADE,

    FOREIGN KEY (route_number)
        REFERENCES routes(route_number)
        ON DELETE CASCADE
);

CREATE TABLE data_quality_issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_type TEXT,
    stop_id INTEGER,
    field_name TEXT,
    raw_value TEXT,
    description TEXT,
    source_row_number INTEGER
);

CREATE INDEX idx_stops_stop_name
ON stops(stop_name);

CREATE INDEX idx_stop_routes_stop_id
ON stop_routes(stop_id);

CREATE INDEX idx_stop_routes_route_number
ON stop_routes(route_number);

CREATE INDEX idx_quality_issues_issue_type
ON data_quality_issues(issue_type);