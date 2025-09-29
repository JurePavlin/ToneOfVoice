1. Create Python Virtual Env for dependencies <br>
python -m venv /path/to/new/virtual/environment
2. Activate Virtual Env<br>
.\path\to\new\virtual\Scripts\activate
3. Install dependencies<br>
pip install -r /path/to/requirements.txt
4. To run the backend<br>
uvicorn app.main:app --reload --port 8000
5. To run the front end<br>
npm run start
