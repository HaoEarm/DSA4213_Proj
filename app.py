from h2o_wave import app, Q, ui, on, data, main
from h2ogpte import H2OGPTE

import pandas as pd

H2OGPTE_URL = "https://h2ogpte.genai.h2o.ai"
try:  # Read API key from local dir
    with open("./API_key.txt", "r") as f:
        H2OGPTE_API_TOKEN = f.read().strip()
except:
    raise Exception("Please follow the setup and place your API key in ./API_key.txt")


def get_genres():
    """
    Loads genre data from local dataset
    Returns a list of strings representing the unique movie genres in alphabetical order
    """
    df = pd.read_json('IMDB_movie_details.json', lines=True)
    genres = list(df['genre'].explode().sort_values().unique())
    return genres


def get_movies():
    """
    Loads movie names from local dataset
    Returns a list of strings representing the unique movie names
    """
    df_movie = pd.read_csv('movies_with_genres.csv')
    movies = list(df_movie['movie_title'].unique())
    return movies


def init_data(q: Q):
    """
    Run all data loading and processing functions.
    Store results in session variables
    """
    q.client.all_movies = get_movies()
    q.client.all_genres = get_genres()


@app("/")
async def serve(q: Q):
    """
    Main Function to boot the app
    In Terminal/Powershell, execute "wave run app.py"
    The q input is handled by h2owave
    """
    if not q.client.initialized:
        init_data(q)
        await init(q)
        q.client.initialized = True

    meta = q.page['meta']
    if q.args.toggle_theme:  # If the user presses the toggle theme button
        meta.theme = q.client.theme = 'h2o-dark' if q.client.theme == 'default' else 'default'

    query_llm(q)  # Generate Movie Recommendations
    update_recommendations(q)  # Update display of recommendations
    await q.page.save()


async def init(q: Q):
    """
    Set up the User Interface and session variables
    """
    q.page['meta'] = ui.meta_card(title='Movie Recomendations', box='', layouts=[  # Different layouts for different window sizes
        ui.layout(
            breakpoint='m',
            zones=[
                ui.zone('header', size='80px'),
                ui.zone('body', size='1000px', direction=ui.ZoneDirection.ROW, zones=[
                    ui.zone('movie_genres', size='300px'),
                    ui.zone('movie_history', size='300px'),
                    ui.zone('right-pane', direction=ui.ZoneDirection.COLUMN, zones=[
                        # ui.zone('trending', size='600px'),
                        ui.zone('movie_recommendations'),
                    ]),
                ]),
            ]
        ),
        ui.layout(
            breakpoint='xl',
            width='1600px',
            zones=[
                ui.zone('header', size='80px'),
                ui.zone('body', size='750px', direction=ui.ZoneDirection.ROW, zones=[
                    ui.zone('movie_genres', size='300px'),
                    ui.zone('movie_history', size='300px'),
                    ui.zone('movie_recommendations'),
                ])
            ]
        )
    ])

    q.page.add('header', ui.header_card(
        box='header',
        title="Movie Recommendations",
        subtitle="A DSA4213 Project",
        icon_color="$yellow",
        items=[ui.button(name='toggle_theme', label='Toggle Theme', primary=True)]
    ))

    # Add elements into the page
    q.page['movie_genres'] = ui.form_card(
        box='movie_genres',
        items=[
            ui.separator('My Favourite Genres'),
            ui.text('Indicate the movie genres you prefer'),
            ui.checklist(
                name='genres',
                choices=[ui.choice(name=str(x), label=str(x)) for x in get_genres()],
            ),
        ]
    )

    q.page['movie_history'] = ui.form_card(
        box='movie_history',
        items=[
            ui.separator('My Movie History'),
            ui.text('Search and add movies to the list of watched movies'),
            ui.picker(
                name='movies',
                choices=[ui.choice(name=str(x), label=str(x)) for x in q.client.all_movies],
            ),
        ]
    )

    q.page['movie_recommendations'] = ui.form_card(
        box='movie_recommendations',
        items=[
            ui.separator('Movies Recommended by LLM'),
            ui.button(name='submit', label='Generate Recommendations!', primary=True),
        ]
    )

    q.client.theme = 'default'
    q.client.recommendations = []


def query_llm(q: Q):
    """
    Craft prompt and use it to query the LLM
    """
    if not q.args.submit:  # Only runs when user presses the submit button
        return

    # q.args.xxx is not persistent. Only has value on change.
    # Create and use q.client.xxx to make favorite genre and movie selections persistent
    if q.args.genres is not None:  # Not None means there's an update
        q.client.genres = q.args.genres  # list of genres selected by user in the 'genres' checklist
    if q.args.movies is not None:  # Not None means there's an update
        q.client.movies = q.args.movies  # list of movies selected by user in the 'movies' picker

    # Craft the Prompt sent to LLM
    msg = ""
    if q.client.genres and q.client.movies:
        msg = f"I have enjoyed the following genres: {', '.join(q.client.genres)} and watched the following movies: {', '.join(q.client.movies)}. From the document, Please recommend me at most 5 good movies based on my taste."
    elif q.client.genres:
        msg = f"I have enjoyed the following genres:{', '.join(q.client.genres)}. From the document, please recommend me at most 5 good movies of the similar genres."
    elif q.client.movies:
        msg = f"I have watched the following movies:{', '.join(q.client.movies)}. From the document, please recommend me at most 5 similar good movies using descriptions."
    elif not q.client.genres and not q.client.movies:
        msg = "From the document, please recommend me 5 good movies."
    else:
        print("Something went wrong creating a prompt")

    if q.client.recommendations:  # Some movies are already recommended
        past_recommendations = "\n\n".join([movie["name"] for movie in q.client.recommendations])
        msg += f"""

Do not recommend the following movies

{past_recommendations}
"""
    # Specify reply format
    msg += """

For every movie recommended, reply in the following format.
Movie Name: <Name of the Movie>
Release Year: <Year of Release>
Description: <A short justification for recommending this movie>
"""

    reply = None
    while not reply:
        try:  # Unstable. API doesn't receive the prompt sometimes so need to retry
            # Create a chat session
            client = H2OGPTE(address=H2OGPTE_URL, api_key=H2OGPTE_API_TOKEN)
            q.client.chat_session_id = client.create_chat_session_on_default_collection()

            with client.connect(q.client.chat_session_id) as session:
                print(msg)  # Prompt sent is printed in terminal
                reply = session.query(
                    message=msg,
                    timeout=40,  # Might need adjustment
                )
            parse_response(q, reply.content)  # Parse LLM response
            display_recommendations(q)  # Display parsed response
        except:
            continue


def parse_response(q, res):
    """
    Parse LLM response and updates list of movie recommendations q.client.recommendations
    res: A string. Response by the LLM
    recommendations: A list of dicts. Currently recommended movie details
    """
    res = res.split("\n")
    for i, line in enumerate(res):
        if "Movie Name:" not in line:
            continue
        try:
            movie_name = line.split("Movie Name: ")[-1].strip()
            if movie_name[0] == '"' and movie_name[-1] == '"':  # Remove quotation marks
                movie_name = movie_name[1:-1]
            movie_year = res[i+1].split("Release Year: ")[-1].strip()
            movie_desc = res[i+2].split("Description: ")[-1].strip()
            if movie_check(q, movie_name):
                q.client.recommendations.append(
                    {"name":movie_name, "year":movie_year, "desc":movie_desc, "discarded":False}
                )
        except Exception as e:  # Response cannot be parsed
            print("Something went wrong when parsing the following portion")
            print(res[i:i+3])
            print(e)


def movie_check(q, movie_name):
    """
    Return True if movie name is valid and has not been recommended or watched.
    """
    if movie_name not in q.client.all_movies:  # Deter hallucination
        return False
    past_recommendations = [movie["name"] for movie in q.client.recommendations]
    if movie_name in past_recommendations:  # Already recommended
        return False
    if q.client.movies and movie_name in q.client.movies:  # User already watched
        return False

    return True


def display_recommendations(q):
    """
    Updates the UI using the list of movie recommendations
    """
    displayed_items = [ui.separator('Movie Recommended by LLM'),
                       ui.button(name='submit', label='Generate Recommendations! (Press Again for More)', primary=True)]

    for i, movie in enumerate(q.client.recommendations):
        if not movie["discarded"]:
            displayed_items.append(ui.text(f'**{movie["name"]}**', size=ui.TextSize.L, name=f'name_{i}'))
            displayed_items.append(ui.text(f'_{movie["year"]}_', name=f'year_{i}'))
            displayed_items.append(ui.text(f'{movie["desc"]}', name=f'desc_{i}'))
            displayed_items.append(ui.buttons(justify="center", items=[
                ui.button(name=f'full_desc_{i}', label='View Full Description'),
                ui.button(name=f'discard_{i}', label='Discard This Recommendation')
            ]))

    q.page['movie_recommendations'].items = displayed_items


def update_recommendations(q):
    """
    Handles user pressing the "View full description" and "Discard" buttons
    """
    for i, movie in enumerate(q.client.recommendations):
        if q.args[f"full_desc_{i}"]:
            get_full_description(q, i)
        if q.args[f"discard_{i}"]:
            q.client.recommendations[i]["discarded"] = True
    display_recommendations(q)  # Update displayed components


def get_full_description(q, movie_index):
    """
    Retrieve a longer description of movie using RAG pipeline
    """
    reply = None
    while not reply:
        try:
            client = H2OGPTE(address=H2OGPTE_URL, api_key=H2OGPTE_API_TOKEN)

            with client.connect(q.client.chat_session_id) as session:
                reply = session.query(
                    message=f'Retrieve the full description for the movie {q.client.recommendations[movie_index]["name"]}',
                    timeout=20
                )
                q.client.recommendations[movie_index]["desc"] = reply.content
        except:
            continue
