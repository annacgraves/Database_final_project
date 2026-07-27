import streamlit as st
import sqlite3
import pandas as pd

st.set_page_config(
    page_title="Spotify Profile",
    page_icon="🎵",
    layout="wide"
)

st.title("Spotify Profile")

col_1, col_2 = st.columns([1, 1], gap="large")

conn = sqlite3.connect("finalDB.sqlite")

query = """
    SELECT
        a.id AS song_id,
        a.name AS song,
        b.name AS artist,
        b.genre,
        b.popularity
    FROM songs a
    LEFT JOIN artist b ON a.artist_id = b.id
"""

df = pd.read_sql(query, conn)

with col_1:
    st.subheader("Current Music Mood(s)")

    my_genres = pd.read_sql(
        """
        SELECT id, genre 
        FROM mood;
        """,
        conn
    )

    if len(my_genres):
        for _, row in my_genres.iterrows():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"""* {row["genre"]}""")

            with col2:
                if st.button("🗑️ Delete", key=f"delete_{row['id']}"):
                    conn.execute(
                        """
                        DELETE FROM mood
                        WHERE rowid = ?
                        """,
                        (row["id"],)
                    )

                    conn.commit()
                    st.rerun()

    else:
        st.info("No genres added yet.")

    st.subheader("Recommendations")

    mood = st.text_input("What genre are you feeling?")

    if st.button("Save Mood"):
        if mood:
            conn.execute("""
                    INSERT INTO mood (genre)
                    VALUES (?)
                """, (mood,)
            )

            conn.commit()
            st.rerun()


    my_genre_list = my_genres["genre"].tolist()

    if len(my_genre_list) > 0:
        conditions = 'WHERE ' + " OR ".join(["b.genre LIKE ?"] * len(my_genre_list))
    else:
        conditions = ""

    params = [f"%{genre}%" for genre in my_genre_list]

    recommendations = pd.read_sql(
        f"""
        SELECT a.name as song, b.name as artist, b.genre as 'genre(s)'
        FROM songs a
        LEFT JOIN artist b ON a.artist_id = b.id
        {conditions}
        ORDER BY RANDOM()
        LIMIT 15;
        """,
        conn, params=params
    )

    if len(recommendations):
        st.dataframe(recommendations, use_container_width=True)

    else:
        st.info("No genres added yet.")


with col_2:
    favorites = pd.read_sql(
        """
            SELECT
                a.id AS id,
                b.name AS Song,
                c.name AS Artist,
                c.genre AS Genre,
                c.popularity AS Popularity
            FROM favorites a
            JOIN songs b
            ON a.song_id = b.id
            JOIN artist c
            ON b.artist_id = c.id
        """, conn
    )


    if len(favorites):
        st.subheader("Your Favorites")

        for _, row in favorites.iterrows():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"- {row['Song']} - {row['Artist']}")

            with col2:
                if st.button("🗑️ Delete", key=f"delete_favorite_{row['id']}"):
                    conn.execute(
                        """
                        DELETE FROM favorites
                        WHERE id = ?
                        """,
                        (row["id"],)
                    )

                    conn.commit()
                    st.rerun()


    else:
        st.info("No favorites added yet.")

    st.divider()

    st.subheader("Add Favorite Songs")

    search = st.text_input("Search for a song")


    if search:
        results = pd.read_sql(
            """
            SELECT
                songs.id,
                songs.name AS song,
                artist.name AS artist
            FROM songs
            JOIN artist
            ON songs.artist_id = artist.id
            WHERE songs.name LIKE ?
            LIMIT 20
            """, conn, params=(f"%{search}%",)
        )

        if len(results):
            song_choice = st.selectbox(
                "Choose a song",
                results["song"] + " - " + results["artist"]
            )

            if st.button("Add to Favorites"):
                selected_id = results[
                    results["song"] + " - " + results["artist"]
                    == song_choice
                ]["id"].iloc[0]

                conn.execute(
                    """
                        INSERT INTO favorites(song_id)
                        VALUES (?)
                    """,
                    (selected_id,)
                )

                conn.commit()
                st.rerun()

conn.close()