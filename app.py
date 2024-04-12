from h2o_wave import app, Q, ui, on, data, main, copy_expando, run_on
from h2ogpte import H2OGPTE

import pandas as pd

H2OGPTE_URL="https://h2ogpte.genai.h2o.ai"
try:  # Read API key from local dir
    with open("./API_key.txt", "r") as f:
        H2OGPTE_API_TOKEN = f.read().strip()
except:
    raise Exception("Please follow the setup and place your API key in ./API_key.txt")

# functions
def get_genres():
    df = pd.read_json('IMDB_movie_details.json', lines=True)
    genres = list(df['genre'].explode().sort_values().unique())
    return genres

def get_movies():
    df_movie = pd.read_csv('movies_with_genres.csv')
    movies = list(df_movie['movie_title'].unique())
    return movies

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
    await q.page.save()


async def init(q: Q):
    """
    Set up the User Interface
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
                        ui.zone('llm_response'),
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
                    ui.zone('llm_response'),
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
    # q.page['suggestions'] = ui.form_card(box='suggestions', items=[])
    # q.page['trending'] = ui.form_card(box='trending', items=[])
    q.page['movie_genres'] = ui.form_card(
        box='movie_genres',
        items=[
            ui.separator('My Favourite Genres'),
            ui.text('Indicate the movie genres you prefer'),
            ui.checklist(
                name='genres',
                choices=[ui.choice(name=str(x), label=str(x)) for x in get_genres()],
            ),
            # ui.button(name='submit', label='Generate Recommendations!', primary=True),
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
            # ui.button(name='submit', label='Generate Recommendations!', primary=True),  # Probably should just have 1 button in the whole page
        ]
    )

    q.page['llm_response'] = ui.form_card(
        box='llm_response',
        items=[
            ui.separator('Movie Recommended by LLM'),
            ui.text(""),  # Init to empty
            ui.button(name='submit', label='Generate Recommendations!', primary=True),  # Probably should just have 1 button in the whole page
        ]
    )

    q.client.theme = 'default'


def init_data(q: Q):
    q.client.all_movies = get_movies()
    q.client.all_genres = get_genres()


def query_llm(q: Q):  # TODO: Should query both using genre and movie history. Need some prompt engineering
    if not q.args.submit:  # Only runs when user presses the submit button
        return

    # q.args.xxx is not persistent. Only has value on change.
    # Create and use q.client.xxx to make it persistent
    if q.args.genres:  # Not None means there's an update
        q.client.genres = q.args.genres  # list of genres selected by user in the 'genres' checklist
    if q.args.movies:  # Not None means there's an update
        q.client.movies = q.args.movies

    if q.client.genres and q.client.movies:
        msg = f"I have enjoyed the following genres: {', '.join(q.client.genres)} and watched the following movies: {', '.join(q.client.movies)}. Please recommend me at most 5 good movies based on my taste."  # Prompt sent to LLM
    elif q.client.genres:
        msg = f"I have enjoyed the following genres:{', '.join(q.client.genres)}, please recommend me at most 5 good movies of the similar genres."
    elif q.client.movies:
        msg = f"I have watched the following movies:{', '.join(q.client.movies)}, please recommend me at most 5 similar good movies."
    elif not q.client.genres and not q.client.movies:
        msg = "Please recommend me 5 movies."
    else:
        msg = "Please check your input"

    reply = None
    while not reply:
        try:  # Unstable. API doesn't receive the prompt sometimes so need to retry
            # Create a chat session
            client = H2OGPTE(address=H2OGPTE_URL, api_key=H2OGPTE_API_TOKEN)
            chat_session_id = client.create_chat_session_on_default_collection()

            with client.connect(chat_session_id) as session:
                print(msg)
                reply = session.query(
                    message=msg,
                    timeout=30,  # Might need adjustment
                )
        except:
            continue
        q.page['llm_response'].items[1].text.content = reply.content  # Update text section in the app

