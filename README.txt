EV DASHBOARD APP - HOW TO RUN
=============================

FILES IN THIS FOLDER
  app.py            -> the main app
  requirements.txt  -> libraries to install
  prep_data.py      -> (optional) makes a small, fast CSV
  run_app.bat       -> double-click to install + run (Windows)
  .gitignore        -> keeps the big CSV out of GitHub

YOU MUST ADD
  Electric_Vehicle_Population_Data.csv  (copy it from your Downloads folder
  into this same folder)

RUN (VS Code terminal, Ctrl + `)
  1) pip install -r requirements.txt
  2) python prep_data.py              (optional; creates ev_data_small.csv)
  3) python -m streamlit run app.py

  Browser opens at http://localhost:8501
  Stop the app with Ctrl + C

UPLOAD TO GITHUB (replace YOUR_USERNAME)
  git init
  git add app.py requirements.txt ev_data_small.csv .gitignore
  git commit -m "EV dashboard app"
  git branch -M main
  git remote add origin https://github.com/YOUR_USERNAME/ev-dashboard-app.git
  git push -u origin main

DEPLOY FREE
  share.streamlit.io -> sign in with GitHub -> Create app
  Repository: YOUR_USERNAME/ev-dashboard-app | Branch: main | File: app.py
