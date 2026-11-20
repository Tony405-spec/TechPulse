CREATE TABLE IF NOT EXISTS ml.watchlist (
  browser_session_id text NOT NULL,
  data_version_id text NOT NULL,
  technology_id text NOT NULL,
  added_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (browser_session_id, data_version_id, technology_id),
  FOREIGN KEY (data_version_id, technology_id)
    REFERENCES sim.technology_metadata(data_version_id, technology_id)
);

CREATE INDEX IF NOT EXISTS ix_ml_watchlist_session
  ON ml.watchlist(browser_session_id, added_at DESC);
