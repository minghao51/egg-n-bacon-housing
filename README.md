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

## References

- https://github.com/crazy4pi314/conda-devcontainer-demo/tree/main