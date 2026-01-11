-- Cassandra Schema Migration Suggestion
-- Generated based on semantic clustering analysis

CREATE KEYSPACE IF NOT EXISTS migrated_db
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 3};

USE migrated_db;

-- Cluster 0: Combines employees
CREATE TABLE IF NOT EXISTS employees_data (
    employees_BirthDate text,
    PRIMARY KEY (employees_BirthDate)
);

-- Cluster 1: Combines customers
CREATE TABLE IF NOT EXISTS customers_data (
    customers_CustomerId text,
    customers_Address text,
    customers_Email text,
    PRIMARY KEY (customers_CustomerId)
);

-- Cluster 2: Combines media_types, tracks
CREATE TABLE IF NOT EXISTS media_types_tracks_data (
    media_types_MediaTypeId text,
    media_types_Name text,
    tracks_TrackId text,
    tracks_Name text,
    tracks_MediaTypeId text,
    tracks_Composer text,
    tracks_Milliseconds text,
    tracks_Bytes text,
    tracks_UnitPrice text,
    PRIMARY KEY (media_types_MediaTypeId)
);

-- Cluster 3: Combines invoice_items
CREATE TABLE IF NOT EXISTS invoice_items_data (
    invoice_items_InvoiceLineId text,
    invoice_items_InvoiceId text,
    invoice_items_TrackId text,
    invoice_items_UnitPrice text,
    invoice_items_Quantity text,
    PRIMARY KEY (invoice_items_InvoiceLineId)
);

-- Cluster 4: Combines employees
CREATE TABLE IF NOT EXISTS employees_data (
    employees_EmployeeId text,
    employees_LastName text,
    employees_FirstName text,
    employees_Title text,
    employees_ReportsTo text,
    employees_HireDate text,
    employees_Address text,
    employees_City text,
    employees_State text,
    employees_Country text,
    employees_Phone text,
    employees_Fax text,
    employees_Email text,
    PRIMARY KEY (employees_EmployeeId)
);

-- Cluster 5: Combines tracks, genres
CREATE TABLE IF NOT EXISTS genres_tracks_data (
    genres_GenreId text,
    genres_Name text,
    tracks_GenreId text,
    PRIMARY KEY (genres_GenreId)
);

-- Cluster 6: Combines employees, customers
CREATE TABLE IF NOT EXISTS customers_employees_data (
    customers_PostalCode text,
    employees_PostalCode text,
    PRIMARY KEY (customers_PostalCode)
);

-- Cluster 7: Combines invoices
CREATE TABLE IF NOT EXISTS invoices_data (
    invoices_InvoiceId text,
    invoices_CustomerId text,
    invoices_InvoiceDate text,
    invoices_BillingAddress text,
    invoices_BillingCity text,
    invoices_BillingState text,
    invoices_BillingCountry text,
    invoices_BillingPostalCode text,
    invoices_Total text,
    PRIMARY KEY (invoices_InvoiceId)
);

-- Cluster 8: Combines artists, tracks, albums
CREATE TABLE IF NOT EXISTS albums_artists_tracks_data (
    albums_AlbumId text,
    albums_Title text,
    albums_ArtistId text,
    artists_ArtistId text,
    artists_Name text,
    tracks_AlbumId text,
    PRIMARY KEY (albums_AlbumId)
);

-- Cluster 9: Combines playlists, playlist_track
CREATE TABLE IF NOT EXISTS playlist_track_playlists_data (
    playlists_PlaylistId text,
    playlists_Name text,
    playlist_track_PlaylistId text,
    playlist_track_TrackId text,
    PRIMARY KEY (playlists_PlaylistId)
);

-- Cluster 10: Combines customers
CREATE TABLE IF NOT EXISTS customers_data (
    customers_FirstName text,
    customers_LastName text,
    customers_Company text,
    customers_City text,
    customers_State text,
    customers_Country text,
    customers_Phone text,
    customers_Fax text,
    customers_SupportRepId text,
    PRIMARY KEY (customers_FirstName)
);
