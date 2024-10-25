# Housing Agent Assist App

- [Notion Page (invite only)](https://www.notion.so/Housing-Agents-App-0c4bdd40940542b2bcd366207428e517?pvs=4)

## Dev setup

- VSC
    - with remote development package with WSL and docker desktop
    ![alt text](image.png)
- codespace
- dvc
    - to use with data setup
    - check .dvc config
    - will need to add aws users setup.

## DVC S3 loging
- To setup aws credentials:
    - login to aws console[https://d-9067d20287.awsapps.com/start/#]
    - copy and set the access key id and secret access key

## Secret/API Keys
use .env.example as template to create .env.

- [onemap](https://www.onemap.gov.sg/apidocs/register)
    - ONEMAP_EMAIL
    - ONEMAP_EMAIL_PASSWORD
- gcp gemini access key
    - GOOGLE_API_KEY
- supabase
    - SUPABASE_URL
    - SUPABASE_KEY

## Dagster Pipeline

The project now includes a Dagster pipeline for data processing and model training. To run the pipeline:

1. Install Dagster and other required dependencies:
   ```
   pip install dagster dagster-pandas scikit-learn joblib dagit
   ```

2. Run the Dagster pipeline using one of the following methods:

   a. Run directly:
   ```
   python pipeline/housing_agent_pipeline.py
   ```

   b. Use Dagster webserver (recommended):
   ```
   dagster dev -f pipeline/housing_agent_pipeline.py
   ```

   This will start the Dagster webserver. Open your browser and navigate to `http://localhost:3000` to access the Dagit UI.

3. In the Dagit UI:
   - Go to the "Assets" tab to see all available assets.
   - Click on "Materialize all" to run the entire pipeline and materialize all assets.
   - Alternatively, you can materialize individual assets by clicking on them and selecting "Materialize".

The pipeline includes the following steps:
- Load and preprocess data
- Split data into training and test sets
- Scale features
- Train a Random Forest model
- Evaluate the model

You can monitor the pipeline execution, view logs, and check asset lineage in the Dagit UI.

## References

- https://github.com/crazy4pi314/conda-devcontainer-demo/tree/main
