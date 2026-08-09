from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

# JSONB en Postgres (production), JSON en SQLite (tests) : même API côté Python.
# Sans cette variante, create_all échoue sur SQLite — le compilateur ne sait pas
# rendre JSONB — et toute la suite de tests qui touche la base meurt avec.
JSONColumn = JSONB().with_variant(JSON(), "sqlite")
