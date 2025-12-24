# MathOCR – API Based Mathematical Expression Recognition

This project is a **Python-based OCR application** that detects mathematical expressions from images
and processes them using external APIs.  
The application is designed with **security in mind**, ensuring that all API credentials are stored
outside the source code.

## Features
- Mathematical expression recognition from images
- API-based OCR processing
- Secure API key management using environment variables
- Modular Python structure for easier maintenance and updates
- Designed for academic and experimental use

## Project Structure

```text
.
├── pppp/
│   └── pppp/
│       ├── api.py
│       ├── apideneme.py
│       └── fixed_mathocr_app.py
├── requirements.txt
├── .gitignore
└── README.md
How It Works
An image containing a mathematical expression is provided to the application.

The image is sent to an external OCR API.

The API returns the recognized mathematical content.

The result is processed and displayed to the user.

API Security (IMPORTANT)
API keys are NOT stored in the source code

All sensitive credentials are loaded from environment variables

A .env file is used locally and is excluded from version control via .gitignore

Example .env file (DO NOT COMMIT THIS FILE):

env
Kodu kopyala
API_KEY=YOUR_API_KEY_HERE
API_SECRET=YOUR_API_SECRET_HERE
Requirements
Python 3.10 or higher

Required Python packages are listed in requirements.txt

Install dependencies:

bash
Kodu kopyala
pip install -r requirements.txt
Running the Project
Run the main application file:

bash
Kodu kopyala
python fixed_mathocr_app.py
Make sure the required environment variables are set before running the application.

Notes
This project is intended for educational and experimental purposes

API usage limits depend on the provider you configure

The codebase can be extended to support additional OCR or math-processing services

Author
Ebubekir Taskiran