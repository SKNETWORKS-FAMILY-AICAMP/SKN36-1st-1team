CREATE TABLE model_master (
    model_key VARCHAR(50) NOT NULL,
    manufacturer_std VARCHAR(50) NOT NULL,
    model_std VARCHAR(100) NOT NULL,
    manufacturer_support_url VARCHAR(1000) NOT NULL,
    PRIMARY KEY (model_key),
    UNIQUE (manufacturer_std, model_std)
);

CREATE TABLE model_mapping (
    mapping_id BIGINT NOT NULL AUTO_INCREMENT,
    model_key VARCHAR(50) NULL,
    generation_name VARCHAR(100) NULL,
    source_type VARCHAR(20) NOT NULL,
    alias_name VARCHAR(255) NOT NULL,
    alias_normalized VARCHAR(255) NOT NULL,
    match_status VARCHAR(20) NOT NULL,
    review_note VARCHAR(500) NULL,
    PRIMARY KEY (mapping_id),
    UNIQUE (source_type, alias_name),
    FOREIGN KEY (model_key) REFERENCES model_master(model_key)
);

CREATE TABLE vehicle_sales (
    model_key VARCHAR(50) NOT NULL,
    sales_year SMALLINT UNSIGNED NOT NULL,
    manufacturer VARCHAR(50) NOT NULL,
    model_original VARCHAR(255) NOT NULL,
    domestic_sales_count BIGINT UNSIGNED NULL,
    verification_status VARCHAR(20) NOT NULL,
    source_url VARCHAR(1000) NOT NULL,
    loaded_at DATE NOT NULL,
    PRIMARY KEY (model_key, sales_year),
    FOREIGN KEY (model_key) REFERENCES model_master(model_key)
);

CREATE TABLE defect_reports (
    defect_report_id BIGINT NOT NULL AUTO_INCREMENT,
    report_date DATE NOT NULL,
    manufacturer VARCHAR(50) NULL,
    model_original VARCHAR(255) NOT NULL,
    model_year SMALLINT UNSIGNED NULL,
    model_key VARCHAR(50) NOT NULL,
    source_url VARCHAR(1000) NOT NULL,
    loaded_at DATE NOT NULL,
    PRIMARY KEY (defect_report_id),
    FOREIGN KEY (model_key) REFERENCES model_master(model_key)
);

CREATE TABLE recall_campaigns (
    recall_id VARCHAR(50) NOT NULL,
    manufacturer VARCHAR(50) NOT NULL,
    model_original VARCHAR(255) NOT NULL,
    model_key VARCHAR(50) NOT NULL,
    production_from DATE NULL,
    production_to DATE NULL,
    recall_start_date DATE NOT NULL,
    recall_count BIGINT UNSIGNED NULL,
    recall_reason TEXT NULL,
    recall_category VARCHAR(50) NOT NULL,
    source_url VARCHAR(1000) NOT NULL,
    official_check_url VARCHAR(1000) NOT NULL,
    loaded_at DATE NOT NULL,
    PRIMARY KEY (recall_id),
    FOREIGN KEY (model_key) REFERENCES model_master(model_key)
);

CREATE TABLE registration_summary (
    registration_id BIGINT NOT NULL AUTO_INCREMENT,
    stat_year SMALLINT UNSIGNED NOT NULL,
    stat_month TINYINT UNSIGNED NULL,
    dimension_type VARCHAR(30) NOT NULL,
    dimension_value VARCHAR(100) NOT NULL,
    registration_count BIGINT UNSIGNED NOT NULL,
    source_url VARCHAR(1000) NOT NULL,
    loaded_at DATE NOT NULL,
    PRIMARY KEY (registration_id)
);

CREATE TABLE faq_master (
    faq_id VARCHAR(50) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    category VARCHAR(50) NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    source_url VARCHAR(1000) NOT NULL,
    collected_at DATETIME NOT NULL,
    PRIMARY KEY (faq_id)
);
