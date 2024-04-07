# DSA4213_Proj

## About the Project

This is a movie recommendation webapp built using H2O Wave and H2OGPTE, based on data from the [MovieLens dataset]('https://www.kaggle.com/datasets/grouplens/movielens-20m-dataset').

The user can indicate their movie genre preferences and movie history in the webapp. Using these information and the help of LLM, the user will receive customized movie recommendations tailored to their likings.

## Setting Up

1. Clone the repository:
    ```shell script
    git clone https://github.com/HaoEarm/DSA4213_Proj
    ```

2. Navigate to this app's directory:
    ```shell script
    cd DSA4213_Proj
    ```
   
3. Create a virtual environment (optional but recommended):
    ```shell script
    python -m venv venv
    ```

4. Activate the virtual environment:
    * On Windows:
    ```shell script
    venv\Scripts\activate
    ```
    * On Unix or MacOS:
    ```shell script
    source venv/bin/activate
    ```

5. Install the required dependencies:
   ```shell script
    pip install -r requirements.txt
    ```

6. Setting up H2O Collection
    * Navigate to the [H2OGPTE website](https://h2ogpte.genai.h2o.ai). Log in via Google or any other valid options.
    * Click `Collections` from the left side-panel.
    * Click `New collection` and selection the appropriate options. (Defaults are fine)
    * In the collection, click `Add documents` and upload a excel file containing the movie data. (or in any other supported format which does not include csv) 
    * Wait for the document to be successfully uploaded.

7. Get an H2OGPTE API Key:
    * Click `APIs` from the left side-panel.
    * Create and copy a new API Key corresponding to the collection created for this project.
    * Create a text file named `API_key.txt` in the project directory and paste the API key inside. 

## Usage

1. Run the application in terminal:
    ```shell script
    wave run app.py
    ```
2. Open your web browser and navigate to http://localhost:10101 to access the app.
