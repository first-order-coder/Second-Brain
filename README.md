# Second Brain - AI-Powered Learning Platform

A comprehensive AI-powered learning platform that converts PDF documents and YouTube videos into interactive flashcards and summaries for enhanced learning.

## 🚀 Features

### 📄 PDF Flashcard Generation
- Upload PDF documents and automatically generate flashcards
- AI-powered content extraction and question generation
- Interactive flashcard interface for spaced repetition learning

### 🎥 YouTube Video Processing
- Extract transcripts from YouTube videos
- Generate flashcards from video content with timestamps
- Support for multiple languages and auto-generated captions

### 📚 Deck Management
- Organize flashcards into study decks
- Save cards from different sources into unified decks
- Track learning progress and performance

### 🧠 AI-Powered Summaries
- Generate citation-backed summaries from source materials
- Interactive summaries with source references
- Support for both PDF and YouTube content

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **Celery** - Distributed task queue for background processing
- **Redis** - Message broker and caching
- **SQLAlchemy** - Database ORM
- **OpenAI API** - AI content generation

### Frontend
- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS framework
- **shadcn/ui** - Modern UI components

### Infrastructure
- **Docker** - Containerized deployment
- **Docker Compose** - Multi-service orchestration

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- OpenAI API key

### Installation

1. **Clone the repository**
   ```bash
   git clone git@github.com:first-order-coder/Second-Brain.git
   cd Second-Brain
   ```

2. **Set up environment variables**
   ```bash
   # Create .env file in the project root
   echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
   ```

3. **Start the application**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## 📖 Usage

### PDF Flashcard Generation
1. Navigate to the main page
2. Upload a PDF document using the file upload interface
3. Wait for processing to complete
4. Review and study the generated flashcards
5. Optionally save cards to a deck for future study

### YouTube Video Processing
1. Paste a YouTube video URL in the YouTube section
2. Select language preferences for transcript extraction
3. Generate flashcards from the video content
4. Review flashcards with timestamps and evidence
5. Save cards to a deck for organized study

### Deck Management
1. Create and manage study decks
2. Add cards from different sources to the same deck
3. Use the deck interface for focused study sessions
4. Track progress and performance over time

## 🏗️ Project Structure

```
├── backend/                 # FastAPI backend application
│   ├── routes/             # API route handlers
│   ├── services/           # Business logic services
│   ├── models.py           # Database models
│   ├── main.py            # FastAPI application entry point
│   └── worker_tasks.py    # Celery background tasks
├── frontend/               # Next.js frontend application
│   ├── app/               # Next.js App Router pages and API routes
│   ├── components/        # React components
│   ├── lib/               # Utility functions and configurations
│   └── types.ts           # TypeScript type definitions
├── docker-compose.yml     # Docker services configuration
└── README.md             # This file
```

## 🔧 Development

### Running in Development Mode

1. **Backend Development**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Frontend Development**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Background Worker**
   ```bash
   cd backend
   celery -A worker_tasks worker --loglevel=info
   ```

### Environment Variables

#### Backend (.env)
```env
OPENAI_API_KEY=your_openai_api_key_here
REDIS_URL=redis://localhost:6379/0
```

#### Frontend (frontend/.env.local)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
ENABLE_DEBUG_ENDPOINTS=false
NEXT_PUBLIC_FEATURE_SUMMARY_CITATIONS=true
```

## 📝 API Documentation

The backend provides comprehensive API documentation available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

- `POST /upload-pdf` - Upload PDF for processing
- `GET /flashcards/{pdf_id}` - Retrieve generated flashcards
- `POST /youtube/flashcards` - Generate flashcards from YouTube video
- `GET /youtube/tracks` - Get available transcript tracks
- `GET /decks` - List all study decks
- `POST /decks` - Create new deck

## 🧪 Testing

### Backend Tests
```bash
cd backend
python -m pytest
```

### Frontend Tests
```bash
cd frontend
npm test
```

## 🚀 Deployment

### Production Deployment

1. **Update environment variables for production**
   ```bash
   # Update docker-compose.prod.yml with production settings
   docker-compose -f docker-compose.prod.yml up -d
   ```

2. **Configure reverse proxy (nginx)**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://localhost:3000;
       }
       
       location /api {
           proxy_pass http://localhost:8000;
       }
   }
   ```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenAI for providing the AI capabilities
- The open-source community for the amazing tools and libraries
- Contributors and users who help improve this platform

## 📞 Support

For support, email support@secondbrain.app or create an issue in the GitHub repository.

---

**Made with ❤️ for learners everywhere**