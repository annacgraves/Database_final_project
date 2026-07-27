import sqlite3
import pandas as pd
import json
import glob
import pickle
import os
import lzma
import streamlit as st

# Creates all required tables including keys and constraints
def create_database(dbpath):
    conn = sqlite3.connect(dbpath)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS artist (
            id varchar(30) NOT NULL PRIMARY KEY,
            name varchar(45) DEFAULT NULL,
            genre varchar(45) DEFAULT NULL,
            popularity int DEFAULT NULL,
            followers int DEFAULT NULL
          );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS songs (
            id varchar(30) NOT NULL PRIMARY KEY,
            name varchar(45) DEFAULT NULL,
            artist_id varchar(30) DEFAULT NULL,
            album longtext,
            CONSTRAINT fk_artist
            FOREIGN KEY (artist_id)
            REFERENCES artist(id)
        );
    ''')


    cursor.execute('''
        CREATE TABLE IF NOT EXISTS listening (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            song_id TEXT,
            ts TEXT,
            skipped INTEGER,
            FOREIGN KEY (song_id) REFERENCES songs(id)
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            song_id TEXT,
            FOREIGN KEY (song_id) REFERENCES songs(id)
        );
    ''')


    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mood (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            genre TEXT
        );
    ''')

    conn.commit()
    conn.close()


# Inserts data from json files into the "listening" table
def insert_listening_data(dbpath):
    conn = sqlite3.connect(dbpath)
    cursor = conn.cursor()

    json_files = glob.glob("data/*.json")

    dfs = []
    for file in json_files:
        with open(file, 'r') as f:
            data = json.load(f)
            df = pd.DataFrame(data)
            dfs.append(df)

    full_df = pd.concat(dfs, ignore_index=True)
    df = full_df.sort_values(by='ts')

    df["spotify_track_uri"] = df["spotify_track_uri"].str.replace("spotify:track:", "")

    listening_rows = df[['spotify_track_uri', 'ts', 'skipped']].values.tolist()

    cursor.executemany("""
    INSERT INTO listening (song_id, ts, skipped)
    VALUES (?, ?, ?)
    """, listening_rows)

    conn.commit()
    conn.close()
    return df


# Gets extra information from cached files from the Spotify API
# Extra note - the Spotify API is only accessible to users with a Premium subscription (I do not have that). I am using cached files I created before that restriction was in place.
def gather_artist_song_info(df):
    with lzma.open("data/spotify_track_features.pkl.xz", "rb") as f:
        track_features = pickle.load(f)

    df_tracks = pd.DataFrame(track_features)
    df_tracks.rename(columns={"uri": "spotify_track_uri"}, inplace=True)
    df_tracks_deduped = df_tracks.drop_duplicates(subset='spotify_track_uri')
    df_tracks_deduped["spotify_track_uri"] = df_tracks_deduped["spotify_track_uri"].str.replace("spotify:track:", "")
    df_merged = df.merge(df_tracks_deduped, on="spotify_track_uri", how="left")

    df_merged['artist_id'] = df_merged['artists'].apply(lambda x: x[0].get("id") if isinstance(x, list) and len(x) > 0 else None)

    with lzma.open("data/spotify_artists.pkl.xz", "rb") as f:
        artist_info = pickle.load(f)

    df_artists = pd.DataFrame(artist_info)
    df_artists['artist_id'] = df_artists['id']
    df_artists_deduped = df_artists.drop_duplicates(subset='artist_id')
    df_merged_2 = df_merged.merge(df_artists_deduped, on="artist_id", how="left", suffixes=("", "_artist"))

    return df_merged_2


# Clean and insert data into "artist" table
def insert_artist(df, dbpath):
    conn = sqlite3.connect(dbpath)
    cursor = conn.cursor()

    artist_df = (
        df[["artist_id", "name_artist", "genres", "popularity_artist", "followers"]]
        .drop_duplicates(subset="artist_id")
        .copy()
    )

    artist_df["genres"] = artist_df["genres"].apply(lambda x: ", ".join(x) if isinstance(x, list) else None)
    artist_df["followers"] = artist_df["followers"].apply(lambda x: x["total"] if isinstance(x, dict) else None)

    artist_df.rename(columns={
        "artist_id": "id",
        "name_artist": "name",
        "genres": "genre",
        "popularity_artist": "popularity"
    }, inplace=True)

    artist_rows = list(artist_df.itertuples(index=False, name=None))

    cursor.executemany("""
        INSERT OR IGNORE INTO artist
        (id, name, genre, popularity, followers)
        VALUES (?, ?, ?, ?, ?)
    """, artist_rows)

    conn.commit()
    conn.close()


# Clean and insert data into "songs" table
def insert_song_info(df, dbpath):
    conn = sqlite3.connect(dbpath)
    cursor = conn.cursor()

    songs_df = (
        df[["id", "name", "artist_id", "album"]]
        .dropna(subset=["id"])
        .drop_duplicates(subset="id")
        .copy()
    )

    songs_df["album"] = songs_df["album"].apply(lambda x: x["name"] if isinstance(x, dict) else x)
    song_rows = list(songs_df.itertuples(index=False, name=None))

    cursor.executemany("""
        INSERT OR IGNORE INTO songs
        (id, name, artist_id, album)
        VALUES (?, ?, ?, ?)
    """, song_rows)

    conn.commit()
    conn.close()

# Implement data insertion
@st.cache_resource
def implement_data_insert():
    dbpath = 'finalDB.sqlite'
    if not os.path.exists(dbpath):
        create_database(dbpath)

        df_1 = insert_listening_data(dbpath)
        df_2 = gather_artist_song_info(df_1)
        insert_artist(df_2, dbpath)
        insert_song_info(df_2, dbpath)

