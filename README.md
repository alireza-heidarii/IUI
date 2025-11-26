## How to Run the Project

1. Install Dependencies
Make sure you have Python 3 installed, then run:
```bash
pip install -r requirements.txt
```
2. Run the Application

Start the Kivy/KivyMD application:
```bash
python main.py
```
3. Install Uvicorn (if not already installed)
```bash
pip install uvicorn
```

4. Start the Backend Server

Run the FastAPI server:
```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```
