import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px

@st.cache_data
def load_data():
    conn = sqlite3.connect("finalDB.sqlite")

    artist = pd.read_sql("""
        SELECT a.name, a.genre, a.popularity, a.followers
        FROM artist a
        LEFT JOIN songs b ON b.artist_id = a.id
        LEFT JOIN listening c ON CONCAT('spotify:track:', b.id) = c.song_id
        WHERE c.ts >= datetime('2025-05-29T01:49:40Z', '-1 month')
        GROUP BY a.name, a.genre, a.popularity, a.followers
        """, conn)
    song = pd.read_sql("SELECT * FROM songs", conn)

    genre = pd.read_sql("""
        SELECT c.genre
        FROM listening a
        LEFT JOIN songs b ON CONCAT('spotify:track:', b.id) = a.song_id
        LEFT JOIN artist c
            ON b.artist_id = c.id
        WHERE c.genre IS NOT NULL
          AND TRIM(c.genre) <> ''
    """, conn)

    top_artist = pd.read_sql("""
        SELECT c.name
        FROM listening a
        LEFT JOIN songs b ON CONCAT('spotify:track:', b.id) = a.song_id
        LEFT JOIN artist c ON b.artist_id = c.id
        WHERE a.ts >= datetime('2025-05-29T01:49:40Z', '-1 month')
        GROUP BY c.name
        ORDER BY COUNT(a.id) DESC
        LIMIT 1
    """, conn)

    top_song = pd.read_sql("""
        SELECT COUNT(a.id), b.name as song, c.name as artist
        FROM listening a
        LEFT JOIN songs b ON CONCAT('spotify:track:', b.id) = a.song_id
        LEFT JOIN artist c ON b.artist_id = c.id
        WHERE a.ts >= datetime('2025-05-29T01:49:40Z', '-1 month')
        GROUP BY b.name, c.name
        ORDER BY COUNT(a.id) DESC
        LIMIT 1
    """, conn)

    conn.close()

    return artist, song, genre, top_artist, top_song

artists, songs, genre_list, artist_top, song_top = load_data()

st.title("Spotify Dashboard")

col1, col2 = st.columns(2)
col1.metric("Top Artist This Month", artist_top["name"].iloc[0])
col2.metric("Top Song This Month", f"{song_top['song'].iloc[0]} by {song_top['artist'].iloc[0]}")

st.divider()

genre_counts = (
    genre_list["genre"]
    .dropna()
    .str.split(",")
    .explode()
    .str.strip()
    .value_counts()
    .head(10)
    .reset_index()
)

genre_counts.columns = ["genre", "count"]

fig = px.pie(
    genre_counts,
    values="count",
    names="genre",
    title="Top 10 Genres by Listen Count"
)

fig.update_traces(textposition="inside", textinfo="percent+label")

st.subheader("Top Genres of All Time")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Most Popular Artists From This Month")

top_artists = artists.sort_values(
    by="popularity",
    ascending=False
).head(10)

st.dataframe(
    top_artists[
        ["name","genre","popularity","followers"]
    ]
)
