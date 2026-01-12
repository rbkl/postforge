# LinkedIn Post Generator

A Django-based tool for generating LinkedIn posts from academic papers (PDFs from arxiv).

## Features

- 📄 **PDF Upload**: Upload academic papers and extract content
- 🤖 **AI Summarization**: Automatically summarize papers using AI
- ✍️ **Style Learning**: Save sample posts to maintain your writing style
- 🖼️ **Image Generation**: Generate or extract relevant images for posts
- 👤 **User Profiles**: Manage your posting preferences and history

## Setup

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Variables

Create a `.env` file in the root directory:

```
OPENAI_API_KEY=your_openai_api_key_here
SECRET_KEY=your_django_secret_key_here
DEBUG=True
```

### 4. Database Setup

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Run the Server

```bash
python manage.py runserver
```

Visit `http://localhost:8000` to use the application.

## Usage

1. **Create a Profile**: Set up your profile with your name and LinkedIn style preferences
2. **Add Sample Posts**: Provide examples of your previous LinkedIn posts to help the AI learn your style
3. **Upload a PDF**: Upload an academic paper (arxiv-style)
4. **Generate Post**: The AI will summarize the paper and create a LinkedIn post in your style
5. **Choose an Image**: Select a generated image or extract one from the PDF

## Tech Stack

- **Backend**: Django 4.2, Django REST Framework
- **Frontend**: Vanilla JavaScript SPA
- **AI**: OpenAI GPT-4 for text, DALL-E for images
- **PDF Processing**: PyMuPDF, pdfplumber

## License

MIT




