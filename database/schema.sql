PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('seller','rider','admin')), active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), csrf TEXT NOT NULL, expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS parcels (id INTEGER PRIMARY KEY, tracking TEXT UNIQUE NOT NULL, seller_id INTEGER NOT NULL REFERENCES users(id), rider_id INTEGER REFERENCES users(id), name TEXT NOT NULL, phone TEXT NOT NULL, address TEXT NOT NULL, weight REAL NOT NULL CHECK(weight > 0 AND weight <= 50), status TEXT NOT NULL DEFAULT 'Registered', proof TEXT, created TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')));
CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, parcel_id INTEGER NOT NULL REFERENCES parcels(id), status TEXT NOT NULL, actor_id INTEGER NOT NULL REFERENCES users(id), created TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')));
CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, actor_id INTEGER, event TEXT NOT NULL, created TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')));
CREATE TABLE IF NOT EXISTS limits (bucket TEXT PRIMARY KEY, count INTEGER NOT NULL, reset REAL NOT NULL);
CREATE INDEX IF NOT EXISTS parcel_owner ON parcels(seller_id);
CREATE INDEX IF NOT EXISTS parcel_rider ON parcels(rider_id);
