from h2o_wave import app, Q, ui, on, data, main, copy_expando, run_on
from h2ogpte import H2OGPTE


H2OGPTE_URL="https://h2ogpte.genai.h2o.ai"
try:  # Read API key from local dir
    with open("./API_key.txt", "r") as f:
        H2OGPTE_API_TOKEN = f.read().strip()
except:
    raise Exception("Please follow the setup and place your API key in ./API_key.txt")


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
                choices=[ui.choice(name=str(x), label=str(x)) for x in q.client.all_genres],
            ),
            ui.button(name='submit', label='Generate Recommendations!', primary=True),
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
            ui.button(name='submit', label='Generate Recommendations!', primary=True),  # Probably should just have 1 button in the whole page
        ]
    )

    q.page['llm_response'] = ui.form_card(
        box='llm_response',
        items=[
            ui.separator('Movie Recommended by LLM'),
            ui.text(""),  # Init to empty
        ]
    )

    q.client.theme = 'default'


def init_data(q: Q):
    # TODO: load actual Movie Dataset and genre list
    q.client.all_movies = ["Toy Story (1995)", "Jumanji (1995)", "Grumpier Old Men (1995)"]
    q.client.all_genres = ["Adventure", "Action", "Comedy", "Drama", "Romance", "Fantasy", "War", "Children", "Animation"]
    q.client.all_genres = sorted(q.client.all_genres)   # Alphabetical order


def query_llm(q: Q):  # TODO: Should query both using genre and movie history. Need some prompt engineering
    if not q.args.submit:  # Only runs when user pressed the submit button
        return

    genres = q.args.genres  # list of genres selected by user in the 'genres' checklist
    if genres:
        msg = f"Recommend me a movie that has some of the following genres: {', '.join(genres)}."  # Prompt sent to LLM
    else:
        msg = "Recommend me some good movies."

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
                    timeout=20,  # Might need adjustment
                )
        except:
            continue
        q.page['llm_response'].items[1].text.content = reply.content  # Update text section in the app

