
CREATE TABLE IF NOT EXISTS pageview_counts (
    pagename VARCHAR(50) NOT NULL,
    pageviewcount INT NOT NULL,
    datetime TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_pageview_counts (
    pagename VARCHAR(50) NOT NULL,
    dailyviews INT NOT NULL,
    date DATE NOT NULL,
    PRIMARY KEY (pagename, date)
);