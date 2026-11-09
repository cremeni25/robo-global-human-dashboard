-- Robô Global v2 — esquema gerado de app/models.py. Não edite à mão.

begin;

CREATE TABLE IF NOT EXISTS rg_anunciantes (
	id VARCHAR(36) NOT NULL, 
	platform VARCHAR(40) NOT NULL, 
	external_id VARCHAR(80) NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	membership VARCHAR(20) NOT NULL, 
	membership_checked_at TIMESTAMP WITH TIME ZONE, 
	approved BOOLEAN NOT NULL, 
	auto_publish BOOLEAN NOT NULL, 
	notes TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_rg_anunciante_externo UNIQUE (platform, external_id)
);

CREATE TABLE IF NOT EXISTS rg_auditoria (
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	actor VARCHAR(80) NOT NULL, 
	action VARCHAR(80) NOT NULL, 
	entity VARCHAR(40) NOT NULL, 
	entity_id VARCHAR(160) NOT NULL, 
	detail JSON NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_rg_auditoria_created_at ON rg_auditoria (created_at);

CREATE TABLE IF NOT EXISTS rg_config (
	key VARCHAR(80) NOT NULL, 
	value JSON NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (key)
);

CREATE TABLE IF NOT EXISTS rg_nichos (
	id VARCHAR(36) NOT NULL, 
	slug VARCHAR(140) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	description TEXT NOT NULL, 
	translations JSON NOT NULL, 
	published BOOLEAN NOT NULL, 
	position INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_rg_nichos_slug UNIQUE (slug)
);

CREATE TABLE IF NOT EXISTS rg_ofertas (
	id VARCHAR(36) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	description TEXT NOT NULL, 
	translations JSON NOT NULL, 
	kind VARCHAR(30) NOT NULL, 
	platform VARCHAR(40) NOT NULL, 
	provider VARCHAR(200) NOT NULL, 
	destination_url VARCHAR(2000) NOT NULL, 
	subid_param VARCHAR(40), 
	external_product_id VARCHAR(120), 
	market VARCHAR(10) NOT NULL, 
	language VARCHAR(10) NOT NULL, 
	currency VARCHAR(3) NOT NULL, 
	commission_estimate NUMERIC(12, 2) NOT NULL, 
	image_url VARCHAR(2000) NOT NULL, 
	price NUMERIC(12, 2), 
	category VARCHAR(300) NOT NULL, 
	source VARCHAR(30) NOT NULL, 
	anunciante_id VARCHAR(36), 
	last_seen_at TIMESTAMP WITH TIME ZONE, 
	active BOOLEAN NOT NULL, 
	published BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_rg_oferta_externa UNIQUE (platform, external_product_id), 
	FOREIGN KEY(anunciante_id) REFERENCES rg_anunciantes (id)
);

CREATE INDEX IF NOT EXISTS ix_rg_ofertas_active ON rg_ofertas (active);

CREATE INDEX IF NOT EXISTS ix_rg_ofertas_anunciante_id ON rg_ofertas (anunciante_id);

CREATE INDEX IF NOT EXISTS ix_rg_ofertas_category ON rg_ofertas (category);

CREATE INDEX IF NOT EXISTS ix_rg_ofertas_external_product_id ON rg_ofertas (external_product_id);

CREATE INDEX IF NOT EXISTS ix_rg_ofertas_published ON rg_ofertas (published);

CREATE TABLE IF NOT EXISTS rg_subnichos (
	nicho_id VARCHAR(36) NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	slug VARCHAR(140) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	description TEXT NOT NULL, 
	translations JSON NOT NULL, 
	published BOOLEAN NOT NULL, 
	position INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_rg_subnichos_slug UNIQUE (nicho_id, slug), 
	FOREIGN KEY(nicho_id) REFERENCES rg_nichos (id)
);

CREATE INDEX IF NOT EXISTS ix_rg_subnichos_nicho_id ON rg_subnichos (nicho_id);

CREATE TABLE IF NOT EXISTS rg_aliases (
	id VARCHAR(36) NOT NULL, 
	oferta_id VARCHAR(36) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(oferta_id) REFERENCES rg_ofertas (id)
);

CREATE TABLE IF NOT EXISTS rg_decisoes (
	id VARCHAR(36) NOT NULL, 
	oferta_id VARCHAR(36) NOT NULL, 
	recomendacao VARCHAR(20) NOT NULL, 
	motivo TEXT NOT NULL, 
	metricas JSON NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	decided_at TIMESTAMP WITH TIME ZONE, 
	decided_by VARCHAR(80) NOT NULL, 
	nota TEXT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(oferta_id) REFERENCES rg_ofertas (id)
);

CREATE INDEX IF NOT EXISTS ix_rg_decisoes_oferta_id ON rg_decisoes (oferta_id);

CREATE TABLE IF NOT EXISTS rg_dores (
	subnicho_id VARCHAR(36) NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	slug VARCHAR(140) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	description TEXT NOT NULL, 
	translations JSON NOT NULL, 
	published BOOLEAN NOT NULL, 
	position INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_rg_dores_slug UNIQUE (subnicho_id, slug), 
	FOREIGN KEY(subnicho_id) REFERENCES rg_subnichos (id)
);

CREATE INDEX IF NOT EXISTS ix_rg_dores_subnicho_id ON rg_dores (subnicho_id);

CREATE TABLE IF NOT EXISTS rg_cliques (
	id VARCHAR(36) NOT NULL, 
	oferta_id VARCHAR(36) NOT NULL, 
	dor_id VARCHAR(36), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	referrer VARCHAR(500) NOT NULL, 
	utm_source VARCHAR(120) NOT NULL, 
	utm_medium VARCHAR(120) NOT NULL, 
	utm_campaign VARCHAR(120) NOT NULL, 
	visitor_hash VARCHAR(64) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(oferta_id) REFERENCES rg_ofertas (id), 
	FOREIGN KEY(dor_id) REFERENCES rg_dores (id)
);

CREATE INDEX IF NOT EXISTS ix_rg_cliques_created_at ON rg_cliques (created_at);

CREATE INDEX IF NOT EXISTS ix_rg_cliques_dor_id ON rg_cliques (dor_id);

CREATE INDEX IF NOT EXISTS ix_rg_cliques_oferta_id ON rg_cliques (oferta_id);

CREATE TABLE IF NOT EXISTS rg_dor_ofertas (
	id VARCHAR(36) NOT NULL, 
	dor_id VARCHAR(36) NOT NULL, 
	oferta_id VARCHAR(36) NOT NULL, 
	priority INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_rg_dor_oferta UNIQUE (dor_id, oferta_id), 
	FOREIGN KEY(dor_id) REFERENCES rg_dores (id), 
	FOREIGN KEY(oferta_id) REFERENCES rg_ofertas (id)
);

CREATE INDEX IF NOT EXISTS ix_rg_dor_ofertas_dor_id ON rg_dor_ofertas (dor_id);

CREATE INDEX IF NOT EXISTS ix_rg_dor_ofertas_oferta_id ON rg_dor_ofertas (oferta_id);

CREATE TABLE IF NOT EXISTS rg_leads (
	id VARCHAR(36) NOT NULL, 
	dor_id VARCHAR(36), 
	email VARCHAR(254) NOT NULL, 
	name VARCHAR(160) NOT NULL, 
	consent BOOLEAN NOT NULL, 
	language VARCHAR(10) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_rg_lead_dor_email UNIQUE (dor_id, email), 
	FOREIGN KEY(dor_id) REFERENCES rg_dores (id)
);

CREATE INDEX IF NOT EXISTS ix_rg_leads_dor_id ON rg_leads (dor_id);

CREATE TABLE IF NOT EXISTS rg_mapeamentos (
	id VARCHAR(36) NOT NULL, 
	termo VARCHAR(200) NOT NULL, 
	campo VARCHAR(20) NOT NULL, 
	dor_id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_rg_mapeamento UNIQUE (termo, dor_id), 
	FOREIGN KEY(dor_id) REFERENCES rg_dores (id)
);

CREATE INDEX IF NOT EXISTS ix_rg_mapeamentos_dor_id ON rg_mapeamentos (dor_id);

CREATE TABLE IF NOT EXISTS rg_conversoes (
	id VARCHAR(36) NOT NULL, 
	platform VARCHAR(40) NOT NULL, 
	external_id VARCHAR(160) NOT NULL, 
	oferta_id VARCHAR(36), 
	clique_id VARCHAR(36), 
	product_id VARCHAR(120) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	gross_amount NUMERIC(12, 2) NOT NULL, 
	commission_amount NUMERIC(12, 2) NOT NULL, 
	currency VARCHAR(3) NOT NULL, 
	occurred_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	source VARCHAR(20) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_rg_conversao_externa UNIQUE (platform, external_id), 
	FOREIGN KEY(oferta_id) REFERENCES rg_ofertas (id), 
	FOREIGN KEY(clique_id) REFERENCES rg_cliques (id)
);

CREATE INDEX IF NOT EXISTS ix_rg_conversoes_oferta_id ON rg_conversoes (oferta_id);

CREATE TABLE IF NOT EXISTS rg_conversao_eventos (
	id VARCHAR(36) NOT NULL, 
	conversao_id VARCHAR(36) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	received_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	raw JSON NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(conversao_id) REFERENCES rg_conversoes (id)
);

CREATE INDEX IF NOT EXISTS ix_rg_conversao_eventos_conversao_id ON rg_conversao_eventos (conversao_id);

commit;
