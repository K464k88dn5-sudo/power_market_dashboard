#!/bin/bash
cd ~/Desktop/power_market_dashboard
python3 -m streamlit run app.py --server.port 8501 --server.headless true
